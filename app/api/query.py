"""
SSE streaming endpoint for the natural language query pipeline.

Implements a two-phase LLM pipeline:
  Phase A — SQL generation (non-streaming, temperature 0.1)
             → validates SQL via sqlglot
             → executes SQL via SQLAlchemy
  Phase B — Narrative description (streaming, temperature 0.3)

SSE event stream:
  event: sql      → validated SQL string
  event: results  → JSON payload with columns/rows
  event: token    → narrative token (or full clarification text)
  event: error    → JSON payload with type/message/detail
  event: done     → stream end marker (empty data)

Exports:
    router  — APIRouter with POST /api/query/ask
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse

from app.config import get_config
from app.db import get_db
from app.query.ollama_client import get_ollama_client
from app.query.prompt import (
    build_narrative_messages,
    build_sql_messages,
    extract_sql_from_response,
)
from app.query.sql_validator import SQLValidationError, validate_sql

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []


# ---------------------------------------------------------------------------
# SQL execution helper
# ---------------------------------------------------------------------------


def execute_query(sql: str, db: Session) -> tuple[list[dict], list[str]]:
    """Execute validated SQL and return (rows, columns).

    Sets statement_timeout to 15 seconds for safety to prevent runaway queries
    from blocking the database.

    Args:
        sql: Validated SELECT SQL string.
        db: SQLAlchemy session.

    Returns:
        Tuple of (rows, columns) where rows is a list of dicts mapping column
        name to value, and columns is an ordered list of column names.
        Decimal and date/datetime values are converted to JSON-safe types.
    """
    db.execute(text("SET statement_timeout = '15000'"))  # 15 seconds in ms
    result = db.execute(text(sql))
    columns = list(result.keys())
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    # Convert Decimal/date values to JSON-safe types
    for row in rows:
        for key, val in row.items():
            if isinstance(val, Decimal):
                row[key] = float(val)
            elif isinstance(val, (date, datetime)):
                row[key] = val.isoformat()
    return rows, columns


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("/ask")
async def ask_query(request: QueryRequest, db: Session = Depends(get_db)):
    """Accept a natural language question and stream results as SSE events.

    Two-phase pipeline:
    - Phase A: Non-streaming SQL generation → validate → execute
    - Phase B: Streaming narrative description of results

    If the LLM responds with a clarification question (no SQL found),
    the response text is streamed as token events without sql/results events.
    """
    config = get_config()

    async def generate():
        try:
            client = get_ollama_client()

            # Phase A: SQL generation (non-streaming for reliable extraction)
            sql_messages = build_sql_messages(
                request.message,
                [m.model_dump() for m in request.history],
            )
            sql_response = await client.chat(
                model=config.ollama_model,
                messages=sql_messages,
                stream=False,
                options={"temperature": 0.1},
            )

            raw_text = sql_response.message.content
            raw_sql = extract_sql_from_response(raw_text)

            # Check if LLM is asking for clarification (no SQL found)
            is_clarification = (
                raw_sql == raw_text
                and not raw_sql.strip().upper().startswith("SELECT")
            )

            if is_clarification:
                yield {"event": "token", "data": raw_text}
                yield {"event": "done", "data": ""}
                return

            # Validate SQL (SELECT-only check)
            validated_sql = validate_sql(raw_sql)
            yield {"event": "sql", "data": validated_sql}

            # Execute SQL
            try:
                rows, columns = execute_query(validated_sql, db)
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "type": "sql_execution",
                        "message": "The query could not be executed.",
                        "detail": str(e),
                    }),
                }
                return

            yield {
                "event": "results",
                "data": json.dumps({"columns": columns, "rows": rows}),
            }

            # Phase B: Narrative generation (streaming)
            narrative_messages = build_narrative_messages(
                request.message, validated_sql, rows, columns
            )
            response_stream = await client.chat(
                model=config.ollama_model,
                messages=narrative_messages,
                stream=True,
                options={"temperature": 0.3},
            )
            async for chunk in response_stream:
                if chunk.message.content:
                    yield {"event": "token", "data": chunk.message.content}

            yield {"event": "done", "data": ""}

        except SQLValidationError as e:
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "sql_invalid",
                    "message": "The generated query was not valid.",
                    "detail": str(e),
                }),
            }
        except Exception as e:
            error_type = "ollama_down" if "connect" in str(e).lower() else "unknown"
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": error_type,
                    "message": (
                        "Something went wrong processing your question."
                        if error_type == "unknown"
                        else "Ollama is not available right now."
                    ),
                    "detail": str(e),
                }),
            }

    return EventSourceResponse(generate())
