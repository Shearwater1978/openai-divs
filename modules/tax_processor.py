import logging
from modules.money_utils import money

logger = logging.getLogger("tax_processor")

def parse_ticker_from_desc(desc: str) -> str:
    try:
        return desc.split("(")[0].strip()
    except Exception:
        return "UNKNOWN"

def get_fx_rate(fx: dict, currency: str, date: str) -> float:
    arr = fx.get(currency.upper()) or []
    for r in arr:
        if r.get("date") == date:
            return float(r.get("rate", 1.0))
    return float(arr[-1].get("rate", 1.0)) if arr else 1.0

def process_tax_line(line: str, fx: dict, report_year: str) -> dict | None:
    # Parse 'Withholding Tax,Data,USD,2025-01-02,<desc>,-0.66'
    parts = [p.strip().strip('"') for p in line.split(",")]
    if len(parts) < 6: return None
    currency, date, desc, amt = parts[2], parts[3], parts[4], parts[5]
    if not date.startswith(report_year): return None
    try:
        amount = money(float(amt))
    except Exception:
        return None
    rate = get_fx_rate(fx, currency, date)
    rec = {
        "ticker": parse_ticker_from_desc(desc),
        "currency": currency,
        "date": date,
        "amount": amount,
        "amountPln": money(amount * rate),
    }
    return rec

def add_tax_to_report(report_data: dict, year: str, rec: dict):
    years = report_data.setdefault("years", [])
    yb = next((y for y in years if y.get("year")==year), None)
    if not yb:
        yb = {"year": year, "dividends": [], "taxes": [], "fx": {}}
        years.append(yb)
    blk = next((b for b in yb["taxes"] if b.get("ticker")==rec["ticker"]), None)
    if not blk:
        blk = {"ticker": rec["ticker"], "currency": rec["currency"], "tax": []}
        yb["taxes"].append(blk)
    blk["tax"].append({
        "date": rec["date"],
        "currency": rec["currency"],
        "amount": rec["amount"],
        "amountPln": rec["amountPln"],
    })
