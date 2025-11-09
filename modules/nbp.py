# modules/nbp.py
# Fetches FX rates from NBP API with on-disk caching.

import json
from pathlib import Path
import urllib.request
from urllib.error import HTTPError, URLError

# Кэш можно переопределить в тестах через monkeypatch
CACHE_DIR = Path("cache") / "nbp"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(currency: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"{currency.upper()}_{start}_{end}.json"


def _http_get_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)
    except (URLError, HTTPError, ValueError):
        return None

# modules/nbp.py

def fetch_nbp_rates_range(currency: str, start: str, end: str) -> list[dict]:
    cur = currency.upper()

    if cur == "PLN":
        return [{"effectiveDate": start, "mid": 1.0}]

    cp = _cache_path(cur, start, end)
    if cp.exists():
        try:
            cached = json.loads(cp.read_text(encoding="utf-8"))
            if isinstance(cached, list) and cached:
                # 🔥 НОРМАЛИЗАЦИЯ ФОРМАТА
                normalized = []
                for r in cached:
                    if "effectiveDate" in r and "mid" in r:
                        normalized.append(r)
                    elif "date" in r and "rate" in r:
                        normalized.append({"effectiveDate": r["date"], "mid": r["rate"]})
                if normalized:
                    return normalized
        except Exception:
            pass

    url = f"https://api.nbp.pl/api/exchangerates/rates/a/{cur}/{start}/{end}?format=json"
    payload = _http_get_json(url)

    rates = []
    if isinstance(payload, dict):
        for r in payload.get("rates", []):
            ed = r.get("effectiveDate")
            mid = r.get("mid")
            if ed and mid is not None:
                rates.append({"effectiveDate": ed, "mid": float(mid)})

    rates.sort(key=lambda x: x["effectiveDate"])

    try:
        cp.write_text(json.dumps(rates, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return rates


# def fetch_nbp_rates_range(currency: str, start: str, end: str) -> list[dict]:
#     """
#     Return list of dicts in RAW NBP format:
#       [{"effectiveDate": "YYYY-MM-DD", "mid": float}, ...]
#     Sorted by date ascending. Results cached to disk.

#     NOTE: If currency == "PLN", return a single-entry list with mid=1.0 for start date.
#     """
#     cur = currency.upper()

#     if cur == "PLN":
#         return [{"effectiveDate": start, "mid": 1.0}]

#     cp = _cache_path(cur, start, end)
#     if cp.exists():
#         try:
#             data = json.loads(cp.read_text(encoding="utf-8"))
#             if isinstance(data, list):
#                 # ожидаем уже нормализованный формат [{"effectiveDate","mid"}, ...]
#                 return data
#         except Exception:
#             pass

#     url = f"https://api.nbp.pl/api/exchangerates/rates/a/{cur}/{start}/{end}?format=json"
#     payload = _http_get_json(url)

#     rates: list[dict] = []
#     if isinstance(payload, dict):
#         for r in payload.get("rates", []):
#             ed = r.get("effectiveDate")
#             mid = r.get("mid")
#             if ed and mid is not None:
#                 try:
#                     rates.append({"effectiveDate": ed, "mid": float(mid)})
#                 except Exception:
#                     continue

#     # сортировка и запись в кэш
#     rates.sort(key=lambda x: x["effectiveDate"])
#     try:
#         cp.write_text(json.dumps(rates, ensure_ascii=False, indent=2), encoding="utf-8")
#     except Exception:
#         pass

#     return rates
