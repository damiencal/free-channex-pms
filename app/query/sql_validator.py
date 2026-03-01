"""
SQL validation using sqlglot AST parsing.

Enforces SELECT-only policy: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER,
multi-statement queries, and parse errors are all rejected.

Exports:
    SQLValidationError  — raised when SQL fails validation
    validate_sql        — parse and validate a SQL string; returns stripped SQL on success
"""

from __future__ import annotations

import sqlglot
from sqlglot import expressions as exp


class SQLValidationError(Exception):
    """Raised when a SQL string fails validation checks."""


def validate_sql(sql: str) -> str:
    """Parse and validate a SQL string, enforcing SELECT-only policy.

    Uses sqlglot's PostgreSQL dialect parser to build an AST. Validates:
    - Parseable SQL (no syntax errors)
    - Non-empty statement
    - Single statement only (no multi-statement batches)
    - SELECT statement only (no DML/DDL)

    Args:
        sql: SQL string to validate (may have leading/trailing whitespace).

    Returns:
        The stripped SQL string if valid.

    Raises:
        SQLValidationError: If the SQL fails any validation check.
    """
    stripped = sql.strip()

    try:
        statements = sqlglot.parse(stripped, read="postgres")
    except Exception as e:
        raise SQLValidationError(f"SQL parse error: {e}") from e

    if not statements or statements[0] is None:
        raise SQLValidationError("Empty SQL")

    if len(statements) > 1:
        raise SQLValidationError("Multiple statements not allowed")

    if not isinstance(statements[0], exp.Select):
        raise SQLValidationError(
            f"Only SELECT is allowed. Got: {type(statements[0]).__name__}"
        )

    return stripped
