"""
Jinja2 template engine with per-property override resolution.

Template resolution priority:
  templates/{property_slug}/ → templates/default/

If a property-specific template exists, it takes priority over the default.
If not, the default is used. This allows per-property customization without
duplicating the full template set.

Startup validation (validate_all_templates) catches undefined variable errors
before the app accepts any requests — fail-fast to prevent runtime surprises.
"""

from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError

log = structlog.get_logger()

# Sample data for startup validation — covers ALL template variables.
# If a template uses a variable not in this dict, validation will catch it.
SAMPLE_BOOKING_DATA = {
    "guest_name": "Test Guest",
    "property_name": "Test Property",
    "checkin_date": "2026-03-01",
    "checkout_date": "2026-03-05",
    "lock_code": "1234",
    "site_number": "100",
    "resort_checkin_instructions": "Located at Test Resort. Please check in at the front desk upon arrival.",
}

# Template names that must exist in templates/default/
REQUIRED_TEMPLATES = ["welcome.txt", "pre_arrival.txt"]


def build_template_env(property_slug: str, templates_dir: str = "templates") -> Environment:
    """Build Jinja2 environment with per-property override resolution.

    Priority: templates/{slug}/ overrides templates/default/
    If templates/{slug}/welcome.txt exists, it's used instead of templates/default/welcome.txt.

    Args:
        property_slug: Short property identifier (e.g., "jay", "minnie").
        templates_dir: Root templates directory. Defaults to "templates" (relative to cwd).

    Returns:
        Configured Jinja2 Environment with StrictUndefined (raises on typos).
    """
    templates_path = Path(templates_dir)
    search_paths = []

    # Property-specific templates take priority (only if directory exists)
    property_dir = templates_path / property_slug
    if property_dir.exists():
        search_paths.append(str(property_dir))

    # Default templates as fallback — always included
    default_dir = templates_path / "default"
    search_paths.append(str(default_dir))

    return Environment(
        loader=FileSystemLoader(search_paths),
        undefined=StrictUndefined,  # Raise on undefined variables — catches typos at render time
    )


def validate_all_templates(property_slugs: list[str], templates_dir: str = "templates") -> None:
    """Validate all templates for all properties render with sample data.

    Called during FastAPI lifespan startup — catches variable typos before
    they reach production. Collects all errors before raising (fail-all-at-once
    pattern consistent with config validation).

    Args:
        property_slugs: List of property slugs to validate templates for.
        templates_dir: Root templates directory. Defaults to "templates".

    Raises:
        SystemExit: If any template is missing or has undefined variables.
    """
    errors: list[str] = []
    templates_path = Path(templates_dir)

    # Check default templates directory exists
    default_dir = templates_path / "default"
    if not default_dir.exists():
        raise SystemExit(f"Template directory not found: {default_dir}")

    # Check all required default templates exist
    for template_name in REQUIRED_TEMPLATES:
        if not (default_dir / template_name).exists():
            errors.append(f"templates/default/{template_name}: required template missing")

    # Validate templates render correctly for each property
    for slug in property_slugs:
        env = build_template_env(slug, templates_dir)
        for template_name in REQUIRED_TEMPLATES:
            try:
                template = env.get_template(template_name)
                template.render(**SAMPLE_BOOKING_DATA)
            except UndefinedError as e:
                errors.append(
                    f"templates (property={slug}) {template_name}: undefined variable — {e}"
                )
            except Exception as e:
                errors.append(f"templates (property={slug}) {template_name}: {e}")

    if errors:
        raise SystemExit(
            "Template validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    log.info("Templates validated", properties=len(property_slugs), templates=len(REQUIRED_TEMPLATES))


def render_template(
    property_slug: str,
    template_name: str,
    data: dict,
    templates_dir: str = "templates",
) -> str:
    """Render a template for a specific property with the given data.

    Args:
        property_slug: Short property identifier (e.g., "jay").
        template_name: Template filename (e.g., "welcome.txt").
        data: Template context variables (must include all required variables).
        templates_dir: Root templates directory. Defaults to "templates".

    Returns:
        Rendered template string.

    Raises:
        UndefinedError: If a required template variable is missing from data.
        TemplateNotFound: If the template doesn't exist in default or property dir.
    """
    env = build_template_env(property_slug, templates_dir)
    template = env.get_template(template_name)
    return template.render(**data)
