# API Reference

Roost exposes a REST API with JSON responses. All endpoints are served at `http://localhost:8000` (or your server address).

## Interactive Documentation

FastAPI auto-generates documentation from the source code type annotations. These are always current:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) — interactive API explorer, try requests directly
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc) — clean reference layout

This guide supplements the interactive docs with workflow context and copy-paste curl examples for the key operations. Use `/docs` or `/redoc` for the full OpenAPI spec, schema details, and response shape definitions.

---

## Workflow: Health Check

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "ok",
  "timestamp": "2026-03-01T12:00:00+00:00",
  "version": "0.1.0",
  "properties": [
    {"slug": "my-cabin", "display_name": "My Cabin"}
  ],
  "database": "connected",
  "ollama": "available"
}
```

`status` is `"ok"` when the database is reachable. Ollama unavailability does not affect `status` — the natural language query feature degrades gracefully if Ollama is not running.

---

## Workflow: Import Booking Data

Roost accepts booking data from three platforms: Airbnb (CSV), VRBO (CSV), and RVshare (JSON). Mercury bank CSVs are imported separately for reconciliation.

After any upload, the response returns immediately with import counts. Background tasks then fire automatically to handle revenue recognition, resort form submission (if applicable), and welcome message scheduling.

### Upload Airbnb CSV

Export a "Transaction History" CSV from the Airbnb host dashboard. Upload it:

```bash
curl -X POST http://localhost:8000/ingestion/airbnb/upload \
  -F "file=@airbnb_transactions.csv"
```

Example response:

```json
{
  "platform": "airbnb",
  "filename": "airbnb_transactions.csv",
  "inserted": 3,
  "updated": 1,
  "skipped": 0
}
```

Ingestion is idempotent — re-importing the same file is safe. Duplicate rows are skipped.

Background tasks fire after the response:
- Revenue recognition: journal entries created for each new booking
- Resort form submission: PDF form filled and emailed (if `auto_submit_threshold` is met)
- Welcome messages: Airbnb welcome is `native_configured` (Airbnb handles natively); Roost logs the status

### Upload VRBO CSV

Export a "Payments Report" CSV from the VRBO host dashboard:

```bash
curl -X POST http://localhost:8000/ingestion/vrbo/upload \
  -F "file=@vrbo_payments.csv"
```

For VRBO bookings, background tasks also schedule welcome messages and email the operator with the rendered message text to send manually on the VRBO platform.

### Upload Mercury Bank CSV

Export a transaction CSV from the Mercury banking dashboard:

```bash
curl -X POST http://localhost:8000/ingestion/mercury/upload \
  -F "file=@mercury_transactions.csv"
```

Bank transactions are stored for reconciliation against booking payouts. No background tasks fire for bank imports.

### RVshare Manual Entry

RVshare does not export a standard CSV format. Enter bookings manually as JSON:

```bash
curl -X POST http://localhost:8000/ingestion/rvshare/entry \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation_code": "RVS-123456",
    "guest_name": "Jane Smith",
    "check_in_date": "2026-04-01",
    "check_out_date": "2026-04-07",
    "net_amount": "875.00",
    "property_slug": "my-cabin",
    "notes": "Early check-in requested"
  }'
```

`confirmation_code` is used as the idempotent key — submitting the same code twice is safe. `property_slug` must match a configured property. `notes` is optional.

---

## Workflow: Generate Financial Reports

All report endpoints accept the same period parameters. The period resolution priority is:

1. `start_date` + `end_date` (explicit range)
2. `month` + `year` (single calendar month)
3. `quarter` + `year` (Q1–Q4)
4. `year` (full calendar year)
5. `ytd=true` (January 1 of current year through today)

If no valid period is specified, the endpoint returns HTTP 422.

### Profit and Loss Report

```bash
# Year-to-date
curl "http://localhost:8000/api/reports/pl?ytd=true"

# Full calendar year
curl "http://localhost:8000/api/reports/pl?year=2026"

# Specific month
curl "http://localhost:8000/api/reports/pl?month=3&year=2026"

# Specific quarter
curl "http://localhost:8000/api/reports/pl?quarter=Q1&year=2026"

# Explicit date range
curl "http://localhost:8000/api/reports/pl?start_date=2026-01-01&end_date=2026-03-31"

# Per-property breakdown (default: combined)
curl "http://localhost:8000/api/reports/pl?year=2026&breakdown=property"
```

Revenue is broken down by platform (Airbnb, VRBO, RVshare) with monthly rows nested under each platform. Expenses are shown as category totals. `net_income` is revenue minus expenses.

### Balance Sheet

The balance sheet requires an `as_of` date:

```bash
curl "http://localhost:8000/api/reports/balance-sheet?as_of=2026-03-31"
```

Shows assets, liabilities (including outstanding loan balances), and equity as a point-in-time snapshot.

### Income Statement

```bash
# Full year, totals view
curl "http://localhost:8000/api/reports/income-statement?year=2026"

# Monthly drill-down
curl "http://localhost:8000/api/reports/income-statement?year=2026&breakdown=monthly"
```

Revenue and expenses broken down by account name. Use `breakdown=monthly` to see month-by-month detail.

---

## Workflow: Natural Language Query

The natural language query endpoint uses Ollama to translate plain-English questions into SQL, execute the query, and stream a narrative answer back.

```bash
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my total revenue last month?"}' \
  --no-buffer
```

The response is a Server-Sent Events (SSE) stream. Use `--no-buffer` with curl to see events as they arrive.

### SSE Event Types

Events arrive as `data: <payload>` lines, each prefixed with `event: <type>`:

| Event | Data format | Description |
|-------|-------------|-------------|
| `sql` | SQL string | The validated SQL query generated from your question |
| `results` | `{"columns": [...], "rows": [...]}` | Query results as JSON |
| `token` | Text fragment | Streaming narrative tokens (arrive one by one) |
| `done` | empty | Stream end marker |
| `error` | `{"type": "...", "message": "...", "detail": "..."}` | Error with type: `ollama_down`, `sql_invalid`, `sql_execution`, or `unknown` |

### Example stream output

```
event: sql
data: SELECT SUM(net_amount) FROM bookings WHERE check_in_date >= '2026-02-01' AND check_in_date < '2026-03-01'

event: results
data: {"columns": ["sum"], "rows": [{"sum": 4250.0}]}

event: token
data: Your total revenue last month was

event: token
data:  $4,250.00

event: done
data:
```

If the LLM asks a clarifying question (no SQL generated), only `token` and `done` events are emitted.

### JavaScript example

```javascript
const response = await fetch('http://localhost:8000/api/query/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'What was my total revenue last month?' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  console.log(text); // process SSE lines
}
```

**Note:** Requires Ollama to be running locally. If Ollama is unavailable, the endpoint returns an `error` event with `type: "ollama_down"` — the rest of Roost continues working normally.

---

## Workflow: Record a Loan Payment

Record monthly P&I payments against a loan. The caller provides the principal/interest split from their lender's amortization schedule — Roost does not compute amortization internally.

```bash
curl -X POST http://localhost:8000/api/accounting/loans/payments \
  -H "Content-Type: application/json" \
  -d '{
    "loan_id": 1,
    "principal": "500.00",
    "interest": "125.00",
    "payment_date": "2026-03-01",
    "payment_ref": "2026-03"
  }'
```

`payment_ref` is the idempotency key — submitting the same `payment_ref` for the same loan twice is safe. The second call returns `{"status": "skipped"}`.

Roost creates balanced journal entries: debit loan liability account + debit interest expense, credit bank asset account.

---

## Workflow: Bank Reconciliation

Reconciliation matches booking payouts to bank deposits. Run it after importing both booking CSVs and a Mercury bank statement.

```bash
# Step 1: Trigger auto-matching
curl -X POST http://localhost:8000/api/accounting/reconciliation/run
```

Response shows counts by outcome:

```json
{
  "auto_matched": 5,
  "needs_review": 2,
  "unmatched_payouts": 1,
  "unmatched_deposits": 3
}
```

```bash
# Step 2: View the unreconciled queue
curl http://localhost:8000/api/accounting/reconciliation/unreconciled
```

The response includes four categories:
- `pending_confirmation`: auto-matched pairs awaiting operator approval
- `needs_review`: deposits the algorithm couldn't match confidently
- `unmatched_payouts`: bookings with no matching bank deposit
- `unmatched_deposits`: deposits with no matching booking

```bash
# Step 3: Confirm an auto-matched pair
curl -X POST http://localhost:8000/api/accounting/reconciliation/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 42,
    "bank_transaction_id": 17,
    "confirmed_by": "operator"
  }'
```

```bash
# Reject a bad match (resets both sides to unmatched)
curl -X POST http://localhost:8000/api/accounting/reconciliation/reject/5
```

---

## Complete Endpoint Reference

All endpoints grouped by module. For full request/response schemas, use the interactive docs at [/docs](http://localhost:8000/docs).

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | DB, Ollama, and config status |

### Ingestion

| Method | Path | Description | Query Parameters |
|--------|------|-------------|-----------------|
| POST | `/ingestion/airbnb/upload` | Upload Airbnb Transaction History CSV | — |
| POST | `/ingestion/vrbo/upload` | Upload VRBO Payments Report CSV | — |
| POST | `/ingestion/mercury/upload` | Upload Mercury bank statement CSV | — |
| POST | `/ingestion/rvshare/entry` | Manual RVshare booking entry (JSON body) | — |
| GET | `/ingestion/history` | Import run history, newest first | `platform`, `limit` |
| GET | `/ingestion/bookings` | Unified booking list | `platform`, `property_slug`, `limit`, `offset` |
| GET | `/ingestion/bank-transactions` | Bank transactions list | `limit`, `offset` |

### Accounting

| Method | Path | Description | Query Parameters |
|--------|------|-------------|-----------------|
| GET | `/api/accounting/journal-entries` | List journal entries | `start_date`, `end_date`, `source_type`, `property_id`, `limit`, `offset` |
| GET | `/api/accounting/journal-entries/{id}` | Single journal entry with all lines | — |
| GET | `/api/accounting/balances` | Account balances by type | `account_type` |
| GET | `/api/accounting/finance-summary` | Uncategorized and unreconciled badge counts | `property_id` |
| POST | `/api/accounting/revenue/recognize` | Operator-triggered recognition for one booking | — |
| POST | `/api/accounting/revenue/recognize-all` | Batch recognition for all unrecognized bookings | — |
| POST | `/api/accounting/expenses` | Record a single expense | — |
| POST | `/api/accounting/expenses/import` | Bulk import expenses from CSV | — |
| GET | `/api/accounting/expenses` | List expenses | `start_date`, `end_date`, `category`, `attribution`, `property_id`, `limit`, `offset` |
| POST | `/api/accounting/loans` | Create a new loan | — |
| POST | `/api/accounting/loans/payments` | Record a loan payment (P&I split) | — |
| GET | `/api/accounting/loans` | List loans with current balances | — |
| POST | `/api/accounting/reconciliation/run` | Trigger batch reconciliation | — |
| GET | `/api/accounting/reconciliation/unreconciled` | Unreconciled queue with pending confirmations | `property_id` |
| POST | `/api/accounting/reconciliation/confirm` | Confirm a reconciliation match | — |
| POST | `/api/accounting/reconciliation/reject/{match_id}` | Reject a match, reset both sides to unmatched | `confirmed_by` |
| GET | `/api/accounting/bank-transactions` | List bank transactions | `categorized`, `start_date`, `end_date`, `min_amount`, `max_amount`, `limit`, `offset` |
| PATCH | `/api/accounting/bank-transactions/categorize` | Bulk categorize bank transactions | — |
| PATCH | `/api/accounting/bank-transactions/{id}/category` | Assign category to a single transaction | — |

### Reports

| Method | Path | Description | Query Parameters |
|--------|------|-------------|-----------------|
| GET | `/api/reports/pl` | Profit and Loss report | `start_date`, `end_date`, `month`, `quarter`, `year`, `ytd`, `breakdown` |
| GET | `/api/reports/balance-sheet` | Balance sheet snapshot | `as_of` (required) |
| GET | `/api/reports/income-statement` | Income statement | `start_date`, `end_date`, `month`, `quarter`, `year`, `ytd`, `breakdown` |

### Compliance

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/compliance/submissions` | List resort form submissions | `status`, `urgent_only`, `limit`, `offset` |
| POST | `/api/compliance/submit/{booking_id}` | Trigger submission for a specific booking |
| POST | `/api/compliance/confirm/{booking_id}` | Mark submission confirmed (n8n webhook) |
| POST | `/api/compliance/approve/{submission_id}` | Approve a preview-mode pending submission |
| POST | `/api/compliance/process-pending` | Batch-process all pending submissions |

### Communication

| Method | Path | Description | Query Parameters |
|--------|------|-------------|-----------------|
| GET | `/api/communication/logs` | List guest message log entries | `status`, `message_type`, `platform`, `limit`, `offset` |
| POST | `/api/communication/confirm/{log_id}` | Mark VRBO/RVshare message as sent by operator | — |

### Dashboard

| Method | Path | Description | Query Parameters |
|--------|------|-------------|-----------------|
| GET | `/api/dashboard/properties` | All properties with id, slug, display_name | — |
| GET | `/api/dashboard/metrics` | YTD revenue, expenses, profit, YoY comparison | `property_id` |
| GET | `/api/dashboard/bookings` | Bookings for calendar view | `property_id`, `start_date`, `end_date` |
| GET | `/api/dashboard/occupancy` | Per-property 12-month occupancy rates | `property_id` |
| GET | `/api/dashboard/actions` | Pending resort forms, messages, unreconciled | `property_id` |

### Query

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/query/ask` | SSE streaming natural language query pipeline |
