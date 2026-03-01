"""
Schema-aware system prompt and message builders for the text-to-SQL LLM pipeline.

Exports:
    SYSTEM_PROMPT                — Schema-aware prompt for SQL generation
    NARRATIVE_SYSTEM_PROMPT      — Prompt for plain-English result narration
    build_sql_messages           — Build Ollama chat message list for SQL phase
    build_narrative_messages     — Build Ollama chat message list for narrative phase
    extract_sql_from_response    — Extract SQL from LLM response text

IMPORTANT: Schema is hardcoded here intentionally.
Do NOT import from app.models — keeping this minimal and controlled means the
prompt is the single source of truth for what the LLM knows about the database.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# SQL Generation System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a PostgreSQL SQL generator for a vacation rental management system.

TASK:
Convert the user's natural language question into a single valid PostgreSQL SELECT query.

RULES:
1. Generate ONLY SELECT statements. Never INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
2. Never perform arithmetic yourself. SQL aggregations (SUM, AVG, COUNT) compute all numbers.
3. If the question is ambiguous (missing property name, time period), ask ONE clarifying
   question instead of guessing. Do NOT output SQL when clarifying.
4. If the question is outside financial/booking scope, respond:
   "I can answer questions about revenue, expenses, bookings, and occupancy."
5. Always output SQL in a ```sql ... ``` code fence. Nothing else outside the fence.

DATABASE SCHEMA:

Table: properties
  id           INTEGER PRIMARY KEY
  slug         VARCHAR(64) UNIQUE        -- short identifier: 'jay', 'minnie'
  display_name VARCHAR(255)              -- human name: 'Jay', 'Minnie'

Table: bookings
  id             INTEGER PRIMARY KEY
  platform       VARCHAR(32)             -- 'airbnb', 'vrbo', 'rvshare', 'direct'
  guest_name     VARCHAR(255)
  check_in_date  DATE
  check_out_date DATE
  net_amount     NUMERIC(10,2)           -- net payout received
  property_id    INTEGER REFERENCES properties(id)

Table: journal_entries
  id          INTEGER PRIMARY KEY
  entry_date  DATE
  description VARCHAR(512)
  source_type VARCHAR(64)               -- 'booking_payout', 'expense', 'loan_payment', etc.
  property_id INTEGER REFERENCES properties(id)  -- nullable (NULL = shared/cross-property)

Table: journal_lines
  id         INTEGER PRIMARY KEY
  entry_id   INTEGER REFERENCES journal_entries(id)
  account_id INTEGER REFERENCES accounts(id)
  amount     NUMERIC(12,2)             -- positive = debit, negative = credit

Table: accounts
  id           INTEGER PRIMARY KEY
  number       INTEGER
  name         VARCHAR(128)
  account_type VARCHAR(32)             -- 'asset', 'liability', 'equity', 'revenue', 'expense'

Table: expenses
  id           INTEGER PRIMARY KEY
  expense_date DATE
  amount       NUMERIC(12,2)           -- always positive (expense amount)
  category     VARCHAR(64)             -- e.g., 'cleaning', 'maintenance', 'utilities'
  description  VARCHAR(512)
  vendor       VARCHAR(255)
  attribution  VARCHAR(32)             -- 'property', 'shared', 'personal'
  property_id  INTEGER REFERENCES properties(id)

SIGN CONVENTION:
Revenue journal_lines have NEGATIVE amounts (credits). To get positive revenue use:
  -SUM(journal_lines.amount)  or  SUM(journal_lines.amount) * -1
for lines joined to accounts WHERE account_type = 'revenue'.

PROPERTY NAMES:
Properties are identified by slug ('jay', 'minnie') or display_name ('Jay', 'Minnie').
Use case-insensitive ILIKE for name matching:
  WHERE p.slug ILIKE 'jay'  or  WHERE p.display_name ILIKE 'Jay'

EXAMPLE QUERIES:

Question: "How much did Jay make this month?"
```sql
SELECT -SUM(jl.amount) AS revenue
FROM journal_lines jl
JOIN journal_entries je ON jl.entry_id = je.id
JOIN accounts a ON jl.account_id = a.id
JOIN properties p ON je.property_id = p.id
WHERE p.slug ILIKE 'jay'
  AND a.account_type = 'revenue'
  AND DATE_TRUNC('month', je.entry_date) = DATE_TRUNC('month', CURRENT_DATE);
```

Question: "Show all Airbnb bookings in January 2026"
```sql
SELECT b.id, b.guest_name, b.check_in_date, b.check_out_date, b.net_amount, p.display_name AS property
FROM bookings b
JOIN properties p ON b.property_id = p.id
WHERE b.platform ILIKE 'airbnb'
  AND b.check_in_date >= '2026-01-01'
  AND b.check_in_date < '2026-02-01'
ORDER BY b.check_in_date;
```

Question: "What were the cleaning expenses for Minnie last quarter?"
```sql
SELECT e.expense_date, e.amount, e.description, e.vendor
FROM expenses e
JOIN properties p ON e.property_id = p.id
WHERE p.slug ILIKE 'minnie'
  AND e.category ILIKE 'cleaning'
  AND e.expense_date >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')
  AND e.expense_date < DATE_TRUNC('quarter', CURRENT_DATE)
ORDER BY e.expense_date;
```
"""

# ---------------------------------------------------------------------------
# Narrative System Prompt (Phase B — plain-English result description)
# ---------------------------------------------------------------------------

NARRATIVE_SYSTEM_PROMPT = """\
You describe SQL query results in plain, conversational English for a non-technical user.

RULES:
1. Use the provided SQL results to write your answer. Never compute or estimate numbers yourself.
2. Format dollar amounts as $X,XXX.XX (e.g., $1,234.56).
3. Be concise — 1-3 sentences.
4. If the results are empty, say so clearly and suggest an alternative query the user might try.
"""

# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

_HISTORY_LIMIT = 10


def build_sql_messages(user_question: str, history: list[dict]) -> list[dict]:
    """Build Ollama chat message list for the SQL generation phase.

    Args:
        user_question: The user's natural language question.
        history: Prior conversation turns as list of {"role": str, "content": str} dicts.
                 Only the last 10 items are included to keep context bounded.

    Returns:
        List of message dicts suitable for the Ollama chat API.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-_HISTORY_LIMIT:])
    messages.append({"role": "user", "content": user_question})
    return messages


def _format_rows_as_text(rows: list[dict], columns: list[str], max_rows: int = 50) -> str:
    """Format query result rows as a plain-text table for the narrative prompt."""
    if not rows:
        return "The query returned no results."

    displayed = rows[:max_rows]
    truncation_note = ""
    if len(rows) > max_rows:
        truncation_note = f"\n(showing first {max_rows} of {len(rows)} rows)"

    # Header
    lines = [" | ".join(str(col) for col in columns)]
    lines.append("-" * len(lines[0]))

    for row in displayed:
        lines.append(" | ".join(str(row.get(col, "")) for col in columns))

    if truncation_note:
        lines.append(truncation_note)

    return "\n".join(lines)


def build_narrative_messages(
    user_question: str,
    sql: str,
    rows: list[dict],
    columns: list[str],
) -> list[dict]:
    """Build Ollama chat message list for the narrative (plain-English) phase.

    Args:
        user_question: The original user question.
        sql: The SQL query that was executed.
        rows: Result rows as list of dicts mapping column name -> value.
        columns: Ordered list of column names for display.

    Returns:
        List of message dicts suitable for the Ollama chat API.
    """
    results_text = _format_rows_as_text(rows, columns)

    user_content = (
        f"The user asked: {user_question}\n\n"
        f"This SQL was executed:\n{sql}\n\n"
        f"Results ({len(rows)} rows):\n{results_text}"
    )

    return [
        {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# SQL extraction from LLM response
# ---------------------------------------------------------------------------

_SQL_FENCE_RE = re.compile(
    r"```(?:sql)?\s*(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def extract_sql_from_response(text: str) -> str:
    """Extract SQL from an LLM response string.

    Tries three strategies in order:
    1. Regex: find ```sql ... ``` or ``` ... ``` code fence
    2. Fallback: find SELECT keyword to end of text
    3. Return original text stripped (caller decides — no SQL means clarification)

    Does NOT raise on missing SQL. Absence of SQL means the LLM is asking a
    clarification question or declining to answer — let the caller handle that.

    Args:
        text: Raw LLM response text.

    Returns:
        Extracted and stripped SQL string, or the original text if no SQL found.
    """
    # Strategy 1: code fence
    match = _SQL_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()

    # Strategy 2: SELECT keyword fallback
    upper = text.upper()
    select_idx = upper.find("SELECT")
    if select_idx != -1:
        return text[select_idx:].strip()

    # Strategy 3: return as-is (clarification or refusal)
    return text.strip()
