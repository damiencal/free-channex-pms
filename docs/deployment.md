# Deployment Guide

This guide walks through deploying Roost on a self-hosted machine using Docker Compose. Following each step in order will take you from a blank server to a running Roost instance.

---

## Prerequisites

**Required:**

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- An SMTP-capable email account — required for resort form email submission and operator notifications. Without SMTP configured, booking form submissions will fail silently. Gmail App Passwords work well (see Step 2).

**Optional:**

- [Ollama](https://ollama.com) running on the host machine — enables the natural language query feature. If Ollama is not available, all other Roost features work normally; only the "Ask a question" query interface is disabled. See [Ollama Setup](#ollama-setup-optional) for details.

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/captainarcher/roost.git
cd roost
```

---

## Step 2: Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and edit each value:

```env
# Database
POSTGRES_DB=rental_management
POSTGRES_USER=rental
POSTGRES_PASSWORD=changeme
DATABASE_URL=postgresql+psycopg://rental:changeme@roost-db:5432/rental_management
```

- `POSTGRES_DB` — the PostgreSQL database name. Default is `rental_management`; leave as-is unless you have a specific reason to change it.
- `POSTGRES_USER` — the PostgreSQL username. Default is `rental`.
- `POSTGRES_PASSWORD` — **change this to a secure password**. The container creates the database with this password on first run. Use the same password in `DATABASE_URL`.
- `DATABASE_URL` — the full connection string used by the application. The hostname must be `roost-db` (the Docker service name). Update the password to match `POSTGRES_PASSWORD`.

```env
# Ollama (optional — system works without it)
OLLAMA_URL=http://host.docker.internal:11434
```

- `OLLAMA_URL` — URL of the Ollama API. `host.docker.internal` resolves to the host machine from within Docker on macOS and Windows. On Linux, use the host gateway IP (typically `http://172.17.0.1:11434`). If you are not using Ollama, leave this value as-is or remove it — the app will start normally with LLM features disabled.

```env
# SMTP (required for resort form email submission)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

- `SMTP_HOST` — your SMTP server hostname (e.g., `smtp.gmail.com` for Gmail, `smtp.fastmail.com` for Fastmail).
- `SMTP_PORT` — `587` for STARTTLS (most providers), `465` for implicit TLS.
- `SMTP_USER` — your email address used to authenticate with the SMTP server.
- `SMTP_PASSWORD` — your SMTP password. **For Gmail, do not use your regular account password.** Instead, create an [App Password](https://support.google.com/accounts/answer/185833) in your Google account security settings. App Passwords are 16-character codes that bypass two-factor authentication prompts.
- `SMTP_FROM_EMAIL` — the sender address that appears on outbound emails. Can be the same as `SMTP_USER`.

> **Important:** Resort form submissions and operator notifications are sent via SMTP. If these variables are empty or incorrect, form submissions will fail. Configure SMTP before proceeding.

---

## Step 3: Configure Base Settings

```bash
cp config/base.example.yaml config/base.yaml
```

Open `config/base.yaml` and review each field:

```yaml
ollama_url: "http://host.docker.internal:11434"
ollama_model: "llama3.2:latest"
archive_dir: "./archive"
airbnb_fee_model: "split_fee"
airbnb_host_fee_rate: 0.03

# Resort compliance settings
confirmations_dir: "./confirmations"
pdf_template_path: "pdf_mappings/sun_retreats_booking.pdf"
pdf_mapping_path: "pdf_mappings/sun_retreats_booking.json"
auto_submit_threshold: 3
resort_contact_name: "CHANGE_ME"
```

**Field reference:**

| Field | Description | Default |
|-------|-------------|---------|
| `ollama_url` | Ollama API URL. Matches the `OLLAMA_URL` in `.env`. | `http://host.docker.internal:11434` |
| `ollama_model` | Ollama model for natural language queries. Run `ollama list` to see available models. | `llama3.2:latest` |
| `archive_dir` | Directory where uploaded CSVs are archived after processing. Mounted as a Docker volume. | `./archive` |
| `airbnb_fee_model` | Airbnb payout fee structure. `split_fee` for the legacy model (guest + host each pay a portion); `host_only` for the post-December 2025 model where the host pays ~15.5%. Check your Airbnb dashboard > Earnings > Payout Details to confirm your model. | `split_fee` |
| `airbnb_host_fee_rate` | Host fee rate as a decimal. `0.03` = 3% for split_fee; `0.155` = 15.5% for host_only. Used to reconstruct gross revenue from net payout. | `0.03` |
| `confirmations_dir` | Directory for resort booking confirmation PDFs received after submission. | `./confirmations` |
| `pdf_template_path` | Path to the blank resort booking form PDF template. | `pdf_mappings/sun_retreats_booking.pdf` |
| `pdf_mapping_path` | Path to the JSON file that maps form fields to property config data. | `pdf_mappings/sun_retreats_booking.json` |
| `auto_submit_threshold` | Days before check-in at which Roost automatically emails the resort booking form. Set to `0` to disable automatic submission entirely (all forms queue as pending for manual approval). | `3` |
| `resort_contact_name` | Name of the resort contact, used in the subject and body of booking form submission emails. Replace `CHANGE_ME` with the actual contact name. | _(empty — required)_ |

---

## Step 4: Configure Properties

Create one YAML file per property in the `config/` directory. Start from the template:

```bash
cp config/config.example.yaml config/my-cabin.yaml
```

Rename `my-cabin.yaml` to match your property slug (e.g., `lake-house.yaml`, `beach-condo.yaml`).

Alternatively, use the interactive setup wizard (from inside the container or local dev environment):

```bash
python manage.py setup
```

**Property config field reference:**

Open `config/my-cabin.yaml` and fill in each field:

```yaml
slug: "my-cabin"
display_name: "My Cabin"
lock_code: "1234"
site_number: "100"
resort_contact_email: "resort@example.com"
resort_checkin_instructions: "Located at Sun Retreats. Please check in at the Welcome Center upon arrival."
host_name: "CHANGE_ME"
host_phone: "555-123-4567"
listing_slug_map:
  "My Listing Title on Airbnb": "my-cabin"
  "12345": "my-cabin"

wifi_password: "network-password"
address: "123 Resort Way, City, ST 12345"
check_in_time: "4:00 PM"
check_out_time: "11:00 AM"
parking_instructions: "Park in designated spot. One vehicle per unit."
local_tips: "Nearest grocery: Publix (0.5 mi). Emergency: 911."
custom:
  pool_code: "5678"
  trash_day: "Tuesday"
```

**Required fields** (the app will refuse to start and list every missing field if any are absent):

| Field | Description |
|-------|-------------|
| `slug` | Short unique identifier for this property. Lowercase, hyphens allowed. Used as the YAML filename, database key, and template folder name. |
| `display_name` | Human-readable name shown in the dashboard and financial reports. |
| `lock_code` | Door lock code included in pre-arrival guest messages. |
| `site_number` | Resort site or unit number used on the booking form submitted to the resort. |
| `resort_contact_email` | Email address the resort booking form is sent to. |
| `resort_checkin_instructions` | Resort-specific check-in instructions included in pre-arrival messages (e.g., where to check in, gate codes). |
| `host_name` | Property owner or host name printed on the resort booking form. Replace `CHANGE_ME`. |
| `host_phone` | Property owner or host phone number printed on the resort booking form. |

**`listing_slug_map`** — this field is critical for automatic booking assignment. When Roost ingests a CSV from Airbnb, VRBO, or RVshare, it looks up the listing title or ID in every property's `listing_slug_map` to determine which property the booking belongs to. Add each listing identifier from your platform exports as a key, with the property slug as the value.

Example: if your Airbnb listing is titled "Jay's Beach House" and has numeric ID 12345:

```yaml
listing_slug_map:
  "Jay's Beach House": "jays-beach-house"
  "12345": "jays-beach-house"
```

**Guest communication fields** (used in pre-arrival messages, defaults to empty if omitted):

| Field | Description |
|-------|-------------|
| `wifi_password` | WiFi network password for the property. |
| `address` | Full street address of the property. |
| `check_in_time` | Check-in time (default: `4:00 PM`). |
| `check_out_time` | Check-out time (default: `11:00 AM`). |
| `parking_instructions` | Where and how to park at the property. |
| `local_tips` | Area information — nearby grocery, restaurants, emergency contacts. |

**`custom` field** — arbitrary key-value pairs that are available in message templates as `{{ custom.key }}`. Add any per-property variable your templates need:

```yaml
custom:
  pool_code: "5678"
  trash_day: "Tuesday"
  mailbox_number: "42B"
```

**Multiple properties:** Create one `.yaml` file per property. There is no limit. All files in `config/` (except `base.yaml` and the example templates) are loaded on startup.

---

## Step 5: Start Roost

```bash
docker compose up -d
```

On first startup, Docker builds the image, starts the PostgreSQL container, waits for it to be healthy, then starts the API container. The API container automatically runs Alembic migrations (including seeding the chart of accounts) before accepting connections.

Database initialization takes approximately 10 seconds on first run.

Check startup logs:

```bash
docker compose logs roost-api --tail 50
```

Look for this line indicating the app is ready:

```
Startup complete — ready to accept requests
```

If the app fails to start, the logs will contain a specific error message — config validation errors list each missing field by name.

---

## Step 6: Verify Installation

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "timestamp": "2026-03-03T12:00:00+00:00",
  "version": "0.1.0",
  "properties": [
    {"slug": "my-cabin", "display_name": "My Cabin"}
  ],
  "database": "connected",
  "ollama": "available"
}
```

- `"status": "ok"` — the app is running
- `"database": "connected"` — PostgreSQL connection is working
- `"properties"` — lists each property loaded from `config/`; if this is empty, check that your property YAML file is in place
- `"ollama": "available"` — Ollama is reachable (shows `"unavailable"` if Ollama is not running, which is fine)

Access the dashboard at `http://localhost:8000`.

> **Note:** `localhost` works when you are on the same machine as the Docker host. For remote access, replace `localhost` with your server's IP address or hostname, and ensure port 8000 is open in your firewall.

---

## Step 7: Import Your First Data

**Upload an Airbnb CSV:**

Export your transaction history from Airbnb (Earnings > Transaction History > Download CSV), then upload it:

```bash
curl -X POST http://localhost:8000/ingestion/airbnb/upload \
  -F "file=@airbnb_transactions.csv"
```

The upload returns immediately. Revenue recognition, resort form queueing, and welcome message scheduling run in the background after the response is sent.

**Check import history:**

```bash
curl http://localhost:8000/ingestion/history
```

**View imported bookings:**

```bash
curl http://localhost:8000/ingestion/bookings
```

For the full API reference, see the interactive Swagger docs at `http://localhost:8000/docs`.

---

## Ollama Setup (Optional)

Ollama enables the natural language query feature — ask questions like "What was my total revenue last month?" in plain English. Without Ollama, all other Roost features work normally.

**Install Ollama on the host machine:**

Follow the instructions at [ollama.com](https://ollama.com) for your operating system.

**Pull the default model:**

```bash
ollama pull llama3.2:latest
```

This is the model specified in `config/base.yaml` (`ollama_model`). Download size is approximately 2 GB.

**Verify Ollama is accessible from Docker:**

The `docker-compose.yml` includes `extra_hosts: - "host.docker.internal:host-gateway"` so the container can reach Ollama on the host. Confirm connectivity:

```bash
curl http://localhost:8000/health
```

The `"ollama"` field should show `"available"`.

**On Linux:** If `host.docker.internal` does not resolve, use the Docker bridge gateway IP instead. Update `.env`:

```env
OLLAMA_URL=http://172.17.0.1:11434
```

And update `config/base.yaml` to match.

---

## Message Templates

Roost generates guest welcome and pre-arrival messages from Jinja2 templates.

Default templates are in `templates/default/`. To customize messaging for a specific property, create a directory matching the property slug and add templates with the same filenames:

```
templates/
├── default/
│   ├── welcome.txt
│   └── pre_arrival.txt
└── my-cabin/
    └── pre_arrival.txt   # Overrides default for my-cabin only
```

Templates have access to all property config fields (e.g., `{{ lock_code }}`, `{{ wifi_password }}`, `{{ check_in_time }}`), custom fields via `{{ custom.key }}`, and booking fields such as `{{ guest_name }}` and `{{ check_in_date }}`.

---

## Resort PDF Forms

Roost fills and emails resort booking forms automatically before each check-in. The form filling is driven by two files:

- `pdf_mappings/sun_retreats_booking.pdf` — the blank PDF form template
- `pdf_mappings/sun_retreats_booking.json` — a JSON mapping that specifies which PDF field name receives which property or booking data

If your resort uses a different form, replace the PDF and update (or create a new) JSON mapping file. Update `pdf_template_path` and `pdf_mapping_path` in `config/base.yaml` to point to your files.

---

## Updating

To update to a newer version:

```bash
git pull
docker compose up -d --build
```

The `--build` flag rebuilds the Docker image with the new code. Alembic migrations run automatically on startup, so the database schema is updated before requests are served.

---

## Troubleshooting

**App fails to start — config validation errors**

The app logs a specific error for each missing or invalid field:

```
Config validation failed:
  - my-cabin.yaml: host_name: Field required
  - my-cabin.yaml: resort_contact_email: Field required
```

Fix each field listed in the error, then restart:

```bash
docker compose restart roost-api
```

**Database connection fails**

Check that `POSTGRES_PASSWORD` in `.env` matches the password in `DATABASE_URL`. The hostname in `DATABASE_URL` must be `roost-db` (not `localhost`) when running inside Docker.

**SMTP authentication fails**

For Gmail: use an App Password, not your account password. Your account must have 2-factor authentication enabled to create App Passwords. Generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

Check SMTP errors in logs:

```bash
docker compose logs roost-api | grep -i smtp
```

**Ollama not reachable**

Verify Ollama is running on the host:

```bash
curl http://localhost:11434/
```

On Linux, ensure the `OLLAMA_URL` in `.env` uses the Docker bridge IP rather than `host.docker.internal`.

**View all logs:**

```bash
docker compose logs roost-api
docker compose logs roost-db
```
