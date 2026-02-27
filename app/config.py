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
