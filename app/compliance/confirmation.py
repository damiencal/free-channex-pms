"""Confirmation file matching and email formatting helpers.

Provides utilities for finding platform booking confirmation PDFs on disk
and composing the resort submission email subject line and body.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path


def find_confirmation_file(
    confirmation_code: str,
    confirmations_dir: str | Path,
) -> Path | None:
    """Find a platform booking confirmation PDF by confirmation code.

    Scans confirmations_dir for PDF files whose name contains
    confirmation_code (case-insensitive).  Returns the first match
    from a sorted listing for deterministic results.

    Args:
        confirmation_code: Platform confirmation code to search for
            (e.g., "HMAB1234").
        confirmations_dir: Directory containing confirmation PDFs.
            The directory need not exist — returns None if absent.

    Returns:
        Path to the first matching PDF, or None if no match found.
    """
    base = Path(confirmations_dir)
    if not base.is_dir():
        return None

    code_lower = confirmation_code.lower()
    for pdf_path in sorted(base.glob("*.pdf")):
        if code_lower in pdf_path.name.lower():
            return pdf_path

    return None


def format_email_subject(
    guest_name: str,
    lot_number: str,
    check_in: date,
    check_out: date,
) -> str:
    """Format the resort submission email subject line.

    Format: "Booking Form - {Guest Name} - Lot {number} - {dates}"

    Date formatting:
    - Same-month stay: "Mar 5-8"
    - Cross-month stay: "Mar 31 - Apr 2"

    Args:
        guest_name: Full guest name (e.g., "John Smith").
        lot_number: Resort site/lot number (e.g., "110").
        check_in: Guest check-in date.
        check_out: Guest check-out date.

    Returns:
        Formatted subject line string.
    """
    if check_in.month == check_out.month:
        dates = f"{check_in.strftime('%b')} {check_in.day}-{check_out.day}"
    else:
        dates = (
            f"{check_in.strftime('%b')} {check_in.day}"
            f" - "
            f"{check_out.strftime('%b')} {check_out.day}"
        )

    return f"Booking Form - {guest_name} - Lot {lot_number} - {dates}"


def format_email_body(
    contact_name: str,
    sender_name: str = "Thomas",
) -> str:
    """Format the resort submission email body.

    Uses a casual, friendly tone per CONTEXT.md guidance.

    Args:
        contact_name: Resort contact's first name (e.g., "CHANGE_ME").
        sender_name: Host/sender name for the sign-off (default: "Thomas").

    Returns:
        Plain-text email body string.
    """
    return (
        f"Hi {contact_name},\n\n"
        "Please find the attached booking form for the upcoming stay. "
        "The booking confirmation is also enclosed.\n\n"
        f"Thanks,\n{sender_name}"
    )
