"""
Roost CLI.

Commands:
  setup            Interactive wizard to create a new property configuration
  list-properties  List all configured properties

Usage:
  python manage.py setup
  python manage.py list-properties
"""

import typer
import questionary
import yaml
from pathlib import Path
from slugify import slugify
import structlog

from app.logging import configure_logging

configure_logging()
log = structlog.get_logger()

cli = typer.Typer(help="Roost CLI")

CONFIG_DIR = Path("config")
EXCLUDED_FILES = {"base.yaml", "config.example.yaml"}


def get_existing_slugs() -> set[str]:
    """Read slugs from existing property config files.

    Scans CONFIG_DIR for *.yaml files, excluding base.yaml and config.example.yaml.
    Returns the set of slugs currently in use (for collision detection).
    """
    slugs = set()
    if CONFIG_DIR.exists():
        for yaml_file in CONFIG_DIR.glob("*.yaml"):
            if yaml_file.name in EXCLUDED_FILES:
                continue
            try:
                data = yaml.safe_load(yaml_file.read_text())
                if data and "slug" in data:
                    slugs.add(data["slug"])
            except Exception:
                pass  # Skip unreadable files
    return slugs


@cli.command()
def setup():
    """Interactive setup wizard — create a new property configuration."""
    typer.echo("=" * 50)
    typer.echo("  Roost — Property Setup")
    typer.echo("=" * 50)
    typer.echo()

    # 1. Property display name
    display_name = questionary.text(
        "Property display name (e.g., \"Jay's Cabin\"):"
    ).ask()
    if not display_name:
        typer.echo("Aborted.")
        raise typer.Exit(1)

    # 2. Slug (with collision detection)
    suggested_slug = slugify(display_name)
    existing_slugs = get_existing_slugs()

    slug = questionary.text(
        "Property slug (short identifier):",
        default=suggested_slug,
    ).ask()
    if not slug:
        typer.echo("Aborted.")
        raise typer.Exit(1)

    slug = slugify(slug)  # Ensure valid slug format (lowercase, hyphens only)
    if slug in existing_slugs:
        typer.echo(f"Error: slug '{slug}' already exists in config/. Choose a different name.")
        raise typer.Exit(1)

    # 3. Property details
    site_number = questionary.text("Resort site/unit number:").ask()
    lock_code = questionary.text("Door lock code:").ask()
    resort_email = questionary.text("Resort contact email:").ask()
    resort_checkin_instructions = questionary.text(
        "Resort check-in instructions (e.g., 'Located at Sun Retreats. Check in at Welcome Center.'):"
    ).ask()

    # 4. Confirmation
    typer.echo()
    typer.echo("Property configuration:")
    typer.echo(f"  Display Name: {display_name}")
    typer.echo(f"  Slug:         {slug}")
    typer.echo(f"  Site Number:  {site_number}")
    typer.echo(f"  Lock Code:    {lock_code}")
    typer.echo(f"  Resort Email: {resort_email}")
    typer.echo(f"  Check-in:     {resort_checkin_instructions}")
    typer.echo()

    confirm = questionary.confirm("Create this property?", default=True).ask()
    if not confirm:
        typer.echo("Aborted.")
        raise typer.Exit(0)

    # 5. Write config file
    config_data = {
        "slug": slug,
        "display_name": display_name,
        "site_number": site_number,
        "lock_code": lock_code,
        "resort_contact_email": resort_email,
        "resort_checkin_instructions": resort_checkin_instructions,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path = CONFIG_DIR / f"{slug}.yaml"
    config_path.write_text(yaml.dump(config_data, default_flow_style=False, sort_keys=False))

    typer.echo()
    typer.echo(f"Config written: {config_path}")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo(f"  1. Review {config_path} and update any placeholder values")
    typer.echo(f"  2. Optionally create template overrides in templates/{slug}/")
    typer.echo(f"  3. Restart the container: docker compose restart app")


@cli.command()
def list_properties():
    """List all configured properties."""
    existing_slugs = get_existing_slugs()
    if not existing_slugs:
        typer.echo("No properties configured. Run 'python manage.py setup' to add one.")
        return
    typer.echo(f"Configured properties ({len(existing_slugs)}):")
    for slug in sorted(existing_slugs):
        typer.echo(f"  - {slug}")


if __name__ == "__main__":
    cli()
