"""Vietnamese Data Normalization Engine (T-208; 04 §5.2; P04; FR-DC-12).

Normalizes Vietnamese dates, currency, percentages, tax codes, and accounting periods
while keeping raw_text intact for review traceability (P01).
"""

import re
import unicodedata
from datetime import datetime
from typing import Any

from app.modules.idp.enums import FieldValueType


def normalize_text(raw: str | None) -> str | None:
    """Trim and normalize Unicode to NFC format."""
    if raw is None:
        return None
    normalized = unicodedata.normalize("NFC", str(raw)).strip()
    return normalized if normalized else None


def normalize_date(raw: str | None) -> str | None:
    """Normalize date strings to ISO YYYY-MM-DD.

    Accepts:
    - dd/mm/yyyy
    - dd-mm-yyyy
    - ngày dd tháng mm năm yyyy
    - YYYY-MM-DD
    """
    if not raw:
        return None
    s = str(raw).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            return None

    m_full = re.search(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", s, re.I)
    if m_full:
        d = int(m_full.group(1))
        m = int(m_full.group(2))
        y = int(m_full.group(3))
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    m_slash = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b", s)
    if m_slash:
        d = int(m_slash.group(1))
        m = int(m_slash.group(2))
        y = int(m_slash.group(3))
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


def _parse_abbreviated_number(num_str: str) -> float:
    """Parse number prefix before units like 'tỷ', 'triệu', 'tr' handling decimal commas/dots."""
    s = num_str.strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2:
            pass  # decimal dot, e.g. 1.2 or 1.25
        else:
            s = s.replace(".", "")
    return float(s)


def normalize_money(raw: Any) -> int | None:
    """Normalize money strings to integer VND (no decimals).

    Accepts:
    - 1.250.000 đ
    - 1,2 tỷ / 1.2 tỷ -> 1200000000
    - 850 tr / 1,25 triệu -> 850000000 / 1250000
    - integer / float
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return int(raw)

    s = str(raw).strip().lower()
    # Check for tỷ (billion = 10^9)
    m_ty = re.search(r"([\d\.\,]+)\s*(?:tỷ|ty|tỉ)\b", s)
    if m_ty:
        val = _parse_abbreviated_number(m_ty.group(1))
        return round(val * 1_000_000_000)

    # Check for triệu / tr (million = 10^6)
    m_tr = re.search(r"([\d\.\,]+)\s*(?:triệu|trieu|tr)\b", s)
    if m_tr:
        val = _parse_abbreviated_number(m_tr.group(1))
        return round(val * 1_000_000)

    # Clean non-digit characters
    cleaned = re.sub(r"[^\d]", "", s)
    if cleaned:
        return int(cleaned)
    return None


def normalize_percent(raw: Any) -> float | None:
    """Normalize percentage strings to decimal (e.g. 12,5% -> 0.125).

    Accepts:
    - 12,5% / 12.5%
    - 10% / 8% / 0%
    - float representation
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        return round(val / 100.0 if val > 1.0 else val, 4)

    s = str(raw).strip().replace("%", "").strip().replace(",", ".")
    try:
        val = float(s)
        return round(val / 100.0 if val > 1.0 else val, 4)
    except ValueError:
        return None


def normalize_tax_code(raw: str | None) -> str | None:
    """Normalize Vietnamese tax code to 10 or 13 digits (format 10 digits or 10-3 digits)."""
    if not raw:
        return None
    digits = re.sub(r"[^\d]", "", str(raw).strip())
    if len(digits) == 10:
        return digits
    elif len(digits) == 13:
        return f"{digits[:10]}-{digits[10:]}"
    return None


def normalize_period(raw: str | None) -> str | None:
    """Normalize accounting periods to YYYY-MM or YYYY-Qn.

    Accepts:
    - T9/2026 / Tháng 9/2026 -> 2026-09
    - Q3/2026 / Quý 3/2026 / Quý III/2026 -> 2026-Q3
    - YYYY-MM / YYYY-Qn
    """
    if not raw:
        return None
    s = str(raw).strip()
    if re.match(r"^\d{4}-(?:0[1-9]|1[0-2])$", s) or re.match(r"^\d{4}-Q[1-4]$", s):
        return s

    # Month period
    m_month = re.search(r"(?:T|tháng\s*)(\d{1,2})[\/\-\s]+(\d{4})", s, re.I)
    if m_month:
        month = int(m_month.group(1))
        year = int(m_month.group(2))
        return f"{year:04d}-{month:02d}"

    # Quarter period
    m_q = re.search(r"(?:Q|quý\s*)([1-4]|I{1,3}|IV)[\/\-\s]+(\d{4})", s, re.I)
    if m_q:
        q_raw = m_q.group(1).upper()
        q_map = {
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "I": "1",
            "II": "2",
            "III": "3",
            "IV": "4",
        }
        q = q_map.get(q_raw, "1")
        year = int(m_q.group(2))
        return f"{year:04d}-Q{q}"

    return None


def normalize_field_value(
    val_type: FieldValueType,
    raw_val: Any,
) -> tuple[Any, str | None]:
    """Normalize a raw value based on its FieldValueType and return (normalized_value, raw_text)."""
    if raw_val is None or raw_val == "":
        return None, None

    raw_text = str(raw_val).strip()

    if val_type == FieldValueType.DATE:
        return normalize_date(raw_text), raw_text
    elif val_type == FieldValueType.MONEY:
        return normalize_money(raw_val), raw_text
    elif val_type == FieldValueType.PERCENT:
        return normalize_percent(raw_val), raw_text
    elif val_type == FieldValueType.TAX_CODE:
        return normalize_tax_code(raw_text), raw_text
    elif val_type == FieldValueType.PERIOD:
        return normalize_period(raw_text), raw_text
    elif val_type in (FieldValueType.TEXT, FieldValueType.PERSON_NAME, FieldValueType.ORG_NAME):
        return normalize_text(raw_text), raw_text
    elif val_type == FieldValueType.NUMBER:
        try:
            return float(raw_text) if "." in raw_text else int(raw_text), raw_text
        except ValueError:
            return None, raw_text

    return raw_val, raw_text
