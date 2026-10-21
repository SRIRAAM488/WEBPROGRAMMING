"""Masking helpers.

DateGuard stores document numbers because users need to tell two documents
apart, but full numbers are never shown on the dashboard. Everything that
reaches a list view goes through ``mask_document_number`` first.
"""

def mask_document_number(value: str | None) -> str | None:
    """Show only the last 4 characters of a document number.

    'DL-1234-9876543' -> '••••9876543'
    """
    if not value:
        return value
    cleaned = value.strip()
    if len(cleaned) <= 4:
        return "*" * len(cleaned)
    return "*" * max(4, len(cleaned) - 4) + cleaned[-4:]