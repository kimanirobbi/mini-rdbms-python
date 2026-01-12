from typing import Any
from datetime import date, datetime

PRIMITIVE_TYPES = {"INT", "TEXT", "FLOAT", "BOOL", "DATE", "TIMESTAMP"}


def coerce_value(value: Any, typ: str):
    """Coerce a Python value to the column type. Raises ValueError on failure.

    DATE values are stored as ISO-format strings (YYYY-MM-DD).
    """
    if value is None:
        return None
    typ = typ.upper()
    if typ == "INT":
        return int(value)
    if typ == "TEXT":
        return str(value)
    if typ == "FLOAT":
        return float(value)
    if typ == "BOOL":
        if isinstance(value, bool):
            return value
        v = str(value).strip().lower()
        if v in ("1", "true", "t", "yes"):
            return True
        if v in ("0", "false", "f", "no"):
            return False
        raise ValueError(f"Cannot coerce {value!r} to BOOL")
    if typ == "DATE":
        # accept date/datetime or ISO date string
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, datetime):
            return value.date().isoformat()
        s = str(value).strip()
        if not s:
            return None
        try:
            # accept ISO format YYYY-MM-DD
            d = date.fromisoformat(s)
            return d.isoformat()
        except Exception:
            raise ValueError(f"Cannot coerce {value!r} to DATE (expected YYYY-MM-DD)")
    if typ == "TIMESTAMP":
        # accept datetime/date or ISO datetime string; store ISO 8601 full datetime
        if isinstance(value, datetime):
            return value.replace(microsecond=0).isoformat()
        if isinstance(value, date) and not isinstance(value, datetime):
            dt = datetime.combine(value, datetime.min.time())
            return dt.replace(microsecond=0).isoformat()
        s = str(value).strip()
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s)
            return dt.replace(microsecond=0).isoformat()
        except Exception:
            # try common space-separated format
            try:
                dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
                return dt.replace(microsecond=0).isoformat()
            except Exception:
                raise ValueError(f"Cannot coerce {value!r} to TIMESTAMP (expected ISO datetime)")
    raise ValueError(f"Unknown type: {typ}")


def validate_type_name(name: str) -> bool:
    return name.upper() in PRIMITIVE_TYPES
