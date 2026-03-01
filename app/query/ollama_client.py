"""
Singleton Ollama AsyncClient wrapper.

Provides a lazy-initialized singleton AsyncClient connected to the configured
Ollama URL. The client is created on first call and reused for all subsequent
calls within the same process lifetime.

Exports:
    get_ollama_client  — return (and lazily create) the singleton AsyncClient
"""

from __future__ import annotations

from ollama import AsyncClient

# Module-level singleton — None until first call to get_ollama_client()
_client: AsyncClient | None = None


def get_ollama_client() -> AsyncClient:
    """Return the singleton Ollama AsyncClient, creating it on first call.

    The client is configured with the host URL from AppConfig.ollama_url.
    Config is read inside the function body (not at import time) so this
    module can be imported before load_app_config() is called.

    Returns:
        Cached AsyncClient instance.
    """
    global _client
    if _client is None:
        from app.config import get_config  # deferred import — config may not be loaded yet

        _client = AsyncClient(host=get_config().ollama_url)
    return _client
