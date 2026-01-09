"""
CodingAgent Serialization Utilities

Helpers for JSON-safe serialization of database query results.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def make_json_serializable(value: Any) -> Any:
    """
    Convert a value to a JSON-serializable type.

    Handles common database types that aren't natively JSON serializable:
    - Decimal -> float
    - datetime/date -> ISO format string
    - UUID -> string
    - bytes -> base64 string

    Args:
        value: Any Python value

    Returns:
        JSON-serializable version of the value
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        value = float(value)
        value = round(value, 6)
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, bytes):
        import base64

        return base64.b64encode(value).decode("ascii")

    if isinstance(value, (list, tuple)):
        return [make_json_serializable(item) for item in value]

    if isinstance(value, dict):
        return {k: make_json_serializable(v) for k, v in value.items()}

    # Basic types (str, int, float, bool) pass through
    return value


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Serialize a database row to JSON-safe format.

    Args:
        row: Dictionary representing a database row

    Returns:
        JSON-serializable dictionary
    """
    return {key: make_json_serializable(value) for key, value in row.items()}


def serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Serialize a list of database rows to JSON-safe format.

    Args:
        rows: List of row dictionaries

    Returns:
        List of JSON-serializable dictionaries
    """
    return [serialize_row(row) for row in rows]
