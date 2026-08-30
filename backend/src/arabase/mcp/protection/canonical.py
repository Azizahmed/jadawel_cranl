import json
from typing import Any

CANONICAL_VALUE_VERSION = 1


def canonicalize_typed_value(field_type: str, value: Any) -> bytes:
    """Return the stable bytes fingerprinted for one serialized field value."""

    return json.dumps(
        {
            "field_type": field_type,
            "v": CANONICAL_VALUE_VERSION,
            "value": value,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
