"""PDF form filling for resort booking forms.

Uses PyMuPDF (pymupdf) to:
1. Detect whether a PDF is AcroForm or XFA
2. Fill AcroForm fields from a JSON mapping
3. Enumerate all form fields for mapping discovery

CRITICAL: Uses field.update() + doc.bake() for cross-viewer compatibility.
doc.bake() embeds appearance streams permanently -- required for macOS Preview
and iOS Mail which do not regenerate appearances on open.
"""

from __future__ import annotations

import json
import structlog
from datetime import date
from pathlib import Path

import pymupdf

log = structlog.get_logger()


def detect_form_type(pdf_path: str) -> str:
    """Detect PDF form type: 'acroform', 'xfa', or 'none'.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        'acroform' if the PDF has fillable AcroForm fields (PyMuPDF can fill).
        'xfa' if the PDF uses XFA forms (PyMuPDF CANNOT fill -- different approach needed).
        'none' if the PDF has no form fields.
    """
    doc = pymupdf.open(pdf_path)
    if not doc.is_pdf:
        return "none"

    cat = doc.pdf_catalog()
    what, value = doc.xref_get_key(cat, "AcroForm")

    if what == "null":
        return "none"

    # AcroForm key exists -- check for XFA sub-key
    if what == "xref":
        acroform_xref = int(value.replace("0 R", "").strip())
        xfa_what, _ = doc.xref_get_key(acroform_xref, "XFA")
        if xfa_what != "null":
            return "xfa"

    return "acroform"


def list_form_fields(pdf_path: str) -> list[dict]:
    """List all form field names, types, and current values in a PDF.

    Use this to inspect the actual resort form and build the JSON mapping.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of dicts with keys: page, name, type, current_value.
    """
    doc = pymupdf.open(pdf_path)
    fields = []
    for page_num, page in enumerate(doc):
        for widget in page.widgets():
            fields.append({
                "page": page_num,
                "name": widget.field_name,
                "type": widget.field_type_string,
                "current_value": widget.field_value,
            })
    return fields


def fill_resort_form(
    template_pdf_path: str,
    mapping_json_path: str,
    booking_data: dict,
    property_data: dict,
) -> bytes:
    """Fill an AcroForm PDF from a JSON field mapping.

    The JSON mapping defines which PDF field gets which value from three sources:
    - "booking": value comes from booking_data dict
    - "property": value comes from property_data dict
    - "static": hardcoded value (e.g., "N/A" for guest phone)

    Uses field.update() per widget + doc.bake() for cross-viewer compatibility.
    doc.bake() embeds appearance streams permanently -- required for macOS Preview
    and iOS Mail which do not regenerate appearances on open.

    Args:
        template_pdf_path: Path to the blank PDF form template.
        mapping_json_path: Path to the JSON field mapping file.
        booking_data: Dict with booking fields (guest_name, check_in_date, check_out_date, etc.)
        property_data: Dict with property fields (site_number, host_name, host_phone, etc.)

    Returns:
        Filled PDF as bytes -- ready for email attachment.

    Raises:
        ValueError: If the PDF is not an AcroForm, or if the mapping file is invalid.
        FileNotFoundError: If the template PDF or mapping JSON does not exist.
    """
    # Validate form type
    form_type = detect_form_type(template_pdf_path)
    if form_type != "acroform":
        raise ValueError(
            f"PDF at {template_pdf_path} is '{form_type}', not 'acroform'. "
            "PyMuPDF can only fill AcroForm PDFs."
        )

    # Load field mapping
    mapping = json.loads(Path(mapping_json_path).read_text())
    field_map = mapping.get("fields", {})

    if not field_map:
        raise ValueError(f"No fields defined in mapping at {mapping_json_path}")

    # Build field values from three source types
    field_values: dict[str, str] = {}
    for pdf_field_name, spec in field_map.items():
        source = spec.get("source")
        if source == "static":
            field_values[pdf_field_name] = spec.get("value", "")
        elif source == "booking":
            raw = booking_data.get(spec.get("field", ""), "")
            # Format dates if format spec provided
            if "format" in spec and isinstance(raw, date):
                fmt = spec["format"]
                # Convert human-readable format to strftime format codes
                fmt = fmt.replace("MM", "%m").replace("DD", "%d").replace("YYYY", "%Y")
                raw = raw.strftime(fmt)
            field_values[pdf_field_name] = str(raw) if raw is not None else ""
        elif source == "property":
            field_values[pdf_field_name] = str(
                property_data.get(spec.get("field", ""), "")
            )
        else:
            log.warning(
                "Unknown source type in PDF mapping",
                field=pdf_field_name,
                source=source,
            )

    # Open template and fill fields
    doc = pymupdf.open(template_pdf_path)

    filled_count = 0
    for page in doc:
        for widget in page.widgets():
            if widget.field_name in field_values:
                widget.field_value = field_values[widget.field_name]
                widget.update()  # Regenerates appearance stream for this field
                filled_count += 1

    # CRITICAL: bake() embeds appearance streams permanently.
    # Required for macOS Preview and iOS Mail -- they do NOT regenerate on open.
    # Do NOT use doc.need_appearances() alone -- it fails on macOS Preview and iOS Mail.
    doc.bake()

    log.info(
        "PDF form filled",
        template=template_pdf_path,
        fields_mapped=len(field_values),
        fields_filled=filled_count,
    )

    return doc.tobytes()
