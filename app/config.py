"""
Application configuration schema using pydantic-settings.

Loading strategy:
  1. Per-property YAML files (config/{slug}.yaml) are discovered dynamically
  2. Base YAML (config/base.yaml) provides system-wide defaults
  3. .env file provides secrets (DATABASE_URL, API keys) — never in YAML
  4. Environment variables override everything

Priority: env vars > .env file > base.yaml
Secrets: DATABASE_URL and all credentials come from .env only
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class PropertyConfig(BaseModel):
    """Configuration for a single rental property.

    All fields are required. Missing fields cause a clear error at startup.
    Example error: "config/jay.yaml: lock_code: Field required"
    """

    slug: str
    """Short identifier (lowercase, hyphens ok). Used as folder name and DB key.
    Example: "jay"
    """

    display_name: str
    """Human-readable name shown in dashboard and reports.
    Example: "Jay"
    """

    lock_code: str
    """Door lock code included in pre-arrival messages."""

    site_number: str
    """Resort site/unit number for booking form.
    Example: "110"
    """

    resort_contact_email: str
    """Email address for booking form submissions."""

    resort_checkin_instructions: str
    """Resort-specific check-in instructions included in pre-arrival messages.
    Example: "Located at Sun Retreats Fort Myers Beach. Please check in at the Welcome Center upon arrival."
    """

    host_name: str
    """Property owner/host name for resort booking form.
    Example: "CHANGE_ME"
    """

    host_phone: str
    """Property owner/host phone for resort booking form.
    Example: "555-123-4567"
    """

    listing_slug_map: dict[str, str] = {}
    """Maps platform listing identifiers to this property slug.
    Keys are platform-specific identifiers found in CSV exports.
    Example: {"Jay's Beach House": "jay", "12345": "jay"}
    The adapter looks up the listing name/ID from the CSV row in this map
    across all properties to find the matching property_id.
    """

    # --- Guest communication fields ---
    wifi_password: str = ""
    """WiFi password for guest pre-arrival message. Empty string if not applicable."""

    address: str = ""
    """Full property address for guest pre-arrival message."""

    check_in_time: str = "4:00 PM"
    """Check-in time shown in pre-arrival message. Default: 4:00 PM."""

    check_out_time: str = "11:00 AM"
    """Check-out time shown in pre-arrival message. Default: 11:00 AM."""

    parking_instructions: str = ""
    """Parking instructions for pre-arrival message. Empty string if none."""

    local_tips: str = ""
    """Local area tips (restaurants, grocery, emergency contacts) for pre-arrival message."""

    custom: dict[str, str] = {}
    """Arbitrary key-value pairs available as template variables.
    Example in YAML:
      custom:
        pool_code: "5678"
        trash_day: "Tuesday"
    Accessed in templates as {{ custom.pool_code }}, {{ custom.trash_day }}.
    """


class AppConfig(BaseSettings):
    """Application-wide configuration loaded from .env + config/base.yaml.

    Secrets (DATABASE_URL) come from .env only.
    System-wide non-secret settings (ollama_url) come from config/base.yaml.
    Per-property settings are loaded separately via load_all_properties().
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="config/base.yaml",
    )

    # --- Secrets (from .env) ---
    database_url: str
    """PostgreSQL connection string. Example: postgresql+psycopg://user:pass@host/db"""

    # --- System-wide defaults (from base.yaml) ---
    ollama_url: str = "http://host.docker.internal:11434"
    """Ollama API base URL. Default works for Docker on macOS/Windows.
    Override in .env for Linux: OLLAMA_URL=http://172.17.0.1:11434
    """

    ollama_model: str = "mistral"
    """Ollama model name for text-to-SQL queries. Default: mistral (Mistral 7B).
    Check available models with: ollama list
    Override in config/base.yaml or .env: OLLAMA_MODEL=mistral:7b-instruct
    """

    archive_dir: str = "./archive"
    """Directory for raw CSV archives. Mount as Docker volume for persistence."""

    airbnb_fee_model: str = "split_fee"
    """Airbnb fee model. One of: 'host_only' or 'split_fee'.

    - 'split_fee': Legacy model — host pays ~3% on top of net payout; guest pays 14-16%.
      The CSV net amount is already after the host deduction.
      Use gross = net / (1 - fee_rate) to reconstruct gross revenue.
    - 'host_only': New model (post-December 2025) — host pays ~15.5% of booking subtotal.
      The CSV net amount is after the full host deduction.
      Use same formula: gross = net / (1 - fee_rate).

    NOTE: Switching fee models requires re-recognizing historical bookings.
    Check Airbnb dashboard > Earnings > Payout Details to confirm your model.
    """

    airbnb_host_fee_rate: float = 0.03
    """Airbnb host fee rate as a decimal.

    - 0.03 = 3% for split_fee model (legacy, default)
    - 0.155 = 15.5% for host_only model (new standard post-December 2025)

    Used with the formula: gross = net / (1 - fee_rate), fee = gross - net.
    NOTE: This is stored as float in config for simplicity; accounting code converts
    to Decimal before any arithmetic to avoid floating-point contamination.
    """

    # --- SMTP (from .env) ---
    smtp_host: str = "smtp.gmail.com"
    """SMTP server hostname. Example: smtp.gmail.com"""

    smtp_port: int = 587
    """SMTP server port. 587 for STARTTLS, 465 for TLS."""

    smtp_user: str = ""
    """SMTP username / email address."""

    smtp_password: str = ""
    """SMTP password or app password."""

    smtp_from_email: str = ""
    """The email address to send from."""

    # --- Compliance (from base.yaml) ---
    confirmations_dir: str = "./confirmations"
    """Directory for resort confirmation PDFs. Mount as Docker volume."""

    pdf_template_path: str = "pdf_mappings/sun_retreats_booking.pdf"
    """Path to the blank resort booking form PDF template."""

    pdf_mapping_path: str = "pdf_mappings/sun_retreats_booking.json"
    """Path to the JSON field mapping for the resort PDF form."""

    auto_submit_threshold: int = 3
    """Days before check-in to trigger automatic form submission."""

    resort_contact_name: str = "CHANGE_ME"
    """Resort contact name used in email subject/body."""

    # --- Populated by load_app_config(), not from YAML directly ---
    properties: list[PropertyConfig] = []
    """All validated property configs. Populated at startup by load_app_config()."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Priority: env vars > .env file > base.yaml."""
        return (env_settings, dotenv_settings, YamlConfigSettingsSource(settings_cls))


def load_all_properties(config_dir: Path) -> list[PropertyConfig]:
    """Discover and validate all per-property YAML config files.

    Scans config_dir for *.yaml files, excluding base.yaml and
    config.example.yaml. Each file is parsed as a PropertyConfig.

    On any validation error, collects ALL errors and raises SystemExit
    with a human-readable message listing every problem.

    Args:
        config_dir: Directory containing property YAML files.

    Returns:
        List of validated PropertyConfig objects, sorted by slug.

    Raises:
        SystemExit: If any config files are invalid or no property files found.
    """
    config_dir = Path(config_dir)
    errors: list[str] = []
    properties: list[PropertyConfig] = []

    yaml_files = sorted(config_dir.glob("*.yaml"))
    property_files = [
        f for f in yaml_files
        if f.name not in ("base.yaml", "config.example.yaml")
    ]

    if not property_files:
        errors.append(
            f"{config_dir}: no property config files found (expected *.yaml)"
        )
        raise SystemExit(
            "Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    slugs_seen: set[str] = set()
    for yaml_file in property_files:
        try:
            data = yaml.safe_load(yaml_file.read_text())
            if data is None:
                errors.append(f"{yaml_file.name}: file is empty")
                continue
            prop = PropertyConfig(**data)
            if prop.slug in slugs_seen:
                errors.append(f"{yaml_file.name}: duplicate slug '{prop.slug}'")
            else:
                slugs_seen.add(prop.slug)
                properties.append(prop)
        except ValidationError as e:
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"{yaml_file.name}: {field}: {err['msg']}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{yaml_file.name}: {e}")

    if errors:
        raise SystemExit(
            "Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return properties


# Module-level singleton — loaded once at startup
_config: AppConfig | None = None


def load_app_config(config_dir: str = "config") -> AppConfig:
    """Load and cache the full application configuration.

    Reads config/base.yaml + .env for AppConfig, then discovers and
    validates all per-property YAML files in config_dir.

    Idempotent — subsequent calls return the cached instance.

    Args:
        config_dir: Directory containing base.yaml and property YAML files.
                    Defaults to "config" (relative to working directory).

    Returns:
        Validated AppConfig with all properties populated.

    Raises:
        SystemExit: If config is invalid (missing fields, parse errors, etc.)
        pydantic_settings.ValidationError: If base AppConfig is invalid (.env missing
            DATABASE_URL, etc.)
    """
    global _config
    if _config is not None:
        return _config
    config = AppConfig()
    config.properties = load_all_properties(Path(config_dir))
    _config = config
    return config


def get_config() -> AppConfig:
    """Return the cached application config.

    Must call load_app_config() before using this function (e.g., during
    FastAPI lifespan startup).

    Returns:
        Cached AppConfig instance.

    Raises:
        RuntimeError: If load_app_config() has not been called yet.
    """
    if _config is None:
        raise RuntimeError(
            "Config not loaded — call load_app_config() first"
        )
    return _config
