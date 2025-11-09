import logging
import re
import csv
from typing import Iterable, List, Optional

logger = logging.getLogger("date_parser")

_PERIOD_RE = re.compile(r'([A-Za-z]+ \d{1,2}, \d{4})\s*[-–]\s*([A-Za-z]+ \d{1,2}, \d{4})')
_MONTHS = {
    "january": "01","february": "02","march": "03","april": "04",
    "may": "05","june": "06","july": "07","august": "08",
    "september": "09","october": "10","november": "11","december": "12",
}

def _convert_long_date(s: str) -> Optional[str]:
    # Convert 'January 1, 2025' -> '2025-01-01'
    try:
        clean = s.replace(",", "").strip()
        m, d, y = clean.split()
        mm = _MONTHS.get(m.lower())
        if not mm: return None
        return f"{y}-{mm}-{int(d):02d}"
    except Exception:
        return None

def _iter_rows(lines: Iterable) -> Iterable[List[str]]:
    # Yield CSV rows as lists (handles BOM, lists, bytes, strings)
    for item in lines:
        if isinstance(item, (bytes, bytearray)):
            item = item.decode("utf-8", errors="replace")
        if isinstance(item, list):
            row = [str(c) for c in item]
            if row: row[0] = row[0].lstrip("\ufeff")
            yield row
            continue
        if isinstance(item, str):
            line = item.lstrip("\ufeff").rstrip()
            for row in csv.reader([line]):
                yield [c.strip() for c in row]
            continue
        # fallback
        for row in csv.reader([str(item)]):
            yield [c.strip() for c in row]

def parse_report_period(file_path: str, lines: Iterable) -> Optional[dict]:
    # Find 'Statement,Data,Period,"January 1, 2025 - January 31, 2025"'
    try:
        for row in _iter_rows(lines):
            if len(row) >= 4 and row[0] == "Statement" and row[1] == "Data" and row[2] == "Period":
                field = row[3]
                m = _PERIOD_RE.search(field) or _PERIOD_RE.search(field.strip().strip('"'))
                if not m:
                    continue
                left, right = m.groups()
                d1, d2 = _convert_long_date(left), _convert_long_date(right)
                if d1 and d2:
                    return {"fromDate": d1, "toDate": d2, "year": d1[:4]}
        logger.warning(f"Could not detect report period for file: {file_path}")
        return None
    except Exception as e:
        logger.warning(f"Could not detect report period for file: {file_path} ({e})")
        return None
