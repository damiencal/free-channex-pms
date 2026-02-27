"""Platform-specific CSV adapter modules.

Each adapter exposes:
    validate_headers(df: pl.DataFrame) -> None
        Raises ValueError with a descriptive message if the DataFrame's
        columns do not match the expected platform CSV structure.

    parse(df: pl.DataFrame) -> tuple[list[BookingRecord], list[str]]
        Normalizes raw CSV data into canonical BookingRecord objects.
        Returns (records, errors). If errors is non-empty, the caller
        (normalizer.ingest_csv) raises ValueError and aborts the import.
        Adapters never write to the database.

Available adapters:
    airbnb  — Airbnb Transaction History CSV        -> list[BookingRecord]
    vrbo    — VRBO Payments Report CSV              -> list[BookingRecord]
    mercury — Mercury bank transaction CSV          -> list[BankTransactionRecord]
"""
