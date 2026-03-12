"""Channex.io HTTP client with rate limiting and automatic retry.

Usage:
    from app.channex.client import get_channex_client

    async with get_channex_client() as client:
        data = await client.get("/properties")

The client:
  - Authenticates every request with the ``user-api-key`` header.
  - Caps concurrent requests via ``asyncio.Semaphore`` (default: 10).
  - Retries transient failures (429 + 5xx) with exponential backoff via tenacity.
  - Raises typed exceptions from ``app.channex.exceptions`` on error.
  - Transparently unwraps JSON:API ``{"data": ...}`` envelope when present.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.channex.exceptions import (
    ChannexAPIError,
    ChannexAuthError,
    ChannexNotFoundError,
    ChannexRateLimitError,
    ChannexServerError,
    ChannexValidationError,
)
from app.config import get_config

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 30.0  # seconds per request
_RETRY_ON = (ChannexRateLimitError, ChannexServerError)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class ChannexClient:
    """Async HTTP client for the Channex.io API v1.

    Lifecycle: use as an async context manager::

        async with ChannexClient(api_key="...") as client:
            properties = await client.get("/properties")

    Args:
        api_key: Channex API key (``user-api-key`` header).
        base_url: API base URL, default ``https://app.channex.io/api/v1``.
        max_concurrent: Maximum simultaneous outbound requests (semaphore size).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://app.channex.io/api/v1",
        max_concurrent: int = 10,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "ChannexClient":
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "user-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=_DEFAULT_TIMEOUT,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Map HTTP error codes to typed ``ChannexAPIError`` subclasses."""
        if response.is_success:
            return
        status = response.status_code
        try:
            body = response.text
        except Exception:
            body = ""
        try:
            detail = response.json()
            message = (
                detail.get("errors", [{}])[0].get("detail")
                or detail.get("message")
                or detail.get("error")
                or str(detail)
            )
        except Exception:
            message = body or f"HTTP {status}"

        if status == 401:
            raise ChannexAuthError(message, status_code=status, response_body=body)
        if status == 404:
            raise ChannexNotFoundError(message, status_code=status, response_body=body)
        if status == 422:
            raise ChannexValidationError(
                message, status_code=status, response_body=body
            )
        if status == 429:
            raise ChannexRateLimitError(message, status_code=status, response_body=body)
        if status >= 500:
            raise ChannexServerError(message, status_code=status, response_body=body)
        raise ChannexAPIError(message, status_code=status, response_body=body)

    # ------------------------------------------------------------------
    # Core request (with retry)
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated request, retrying on transient errors.

        Returns the parsed JSON body, unwrapping ``{"data": ...}`` when present.
        """
        assert self._http is not None, (
            "ChannexClient used outside async context manager. "
            "Use: async with ChannexClient(...) as client: ..."
        )

        @retry(
            wait=wait_exponential(multiplier=1, min=1, max=60),
            stop=stop_after_attempt(5),
            retry=retry_if_exception_type(_RETRY_ON),
            reraise=True,
        )
        async def _execute() -> Any:
            async with self._semaphore:
                log.debug(
                    "channex_request",
                    method=method.upper(),
                    path=path,
                )
                response = await self._http.request(method, path, **kwargs)  # type: ignore[union-attr]
                self._raise_for_status(response)
                if response.status_code == 204 or not response.content:
                    return None
                body = response.json()
                # Transparently unwrap JSON:API single-resource envelope
                if isinstance(body, dict) and "data" in body and "meta" not in body:
                    return body["data"]
                return body

        return await _execute()

    # ------------------------------------------------------------------
    # Convenience verbs
    # ------------------------------------------------------------------

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Any = None) -> Any:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, json: Any = None) -> Any:
        return await self._request("PUT", path, json=json)

    async def patch(self, path: str, json: Any = None) -> Any:
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

    # ------------------------------------------------------------------
    # Pagination helper
    # ------------------------------------------------------------------

    async def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        per_page: int = 25,
    ) -> list[Any]:
        """Fetch all pages for a list endpoint, returning combined ``data`` items.

        Channex uses page-number pagination::

            ?pagination[limit]=25&pagination[page]=1

        The response ``meta`` contains ``total`` (total item count) and ``limit``
        (items per page), used to compute whether another page exists.

        Returns a flat list of all items across all pages.
        """
        base_params: dict[str, Any] = dict(params or {})
        base_params["pagination[limit]"] = per_page
        items: list[Any] = []
        page = 1

        while True:
            base_params["pagination[page]"] = page
            body = await self._request("GET", path, params=base_params)

            # paginate() bypasses _request's envelope unwrapping — handle manually
            if isinstance(body, dict):
                page_items = body.get("data", body)
                meta = body.get("meta", {})
            else:
                page_items = body if body is not None else []
                meta = {}

            if isinstance(page_items, list):
                items.extend(page_items)
            elif page_items is not None:
                items.append(page_items)

            # Channex returns meta.total (total items) and meta.limit (page size).
            # Fall back to the legacy meta.pagination.total_pages key as well.
            total_items = meta.get("total")
            page_limit = meta.get("limit", per_page)
            pagination = meta.get("pagination", {})
            legacy_pages = pagination.get("total_pages") or pagination.get("pages")

            if legacy_pages is not None:
                if page >= int(legacy_pages):
                    break
            elif total_items is not None and page_limit:
                import math

                total_pages = math.ceil(int(total_items) / int(page_limit))
                if page >= total_pages:
                    break
            else:
                # No pagination info — assume single page
                break
            page += 1

        return items


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_channex_client() -> ChannexClient:
    """Create a ``ChannexClient`` configured from the app singleton config.

    Call this inside an ``async with`` block::

        async with get_channex_client() as client:
            ...

    Raises:
        ChannexAuthError: If ``channex_api_key`` is empty.
    """
    config = get_config()
    if not config.channex_api_key:
        raise ChannexAuthError(
            "CHANNEX_API_KEY is not configured. Set it in .env.",
            status_code=401,
        )
    return ChannexClient(
        api_key=config.channex_api_key,
        base_url=config.channex_base_url,
        max_concurrent=config.channex_rate_limit,
    )
