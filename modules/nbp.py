# NBP API client with on-disk caching (stdlib only, urlopen-based for easy patching in tests)
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CACHE_DIR = Path("cache/nbp")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cache_path(ccy: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"{ccy.upper()}_{start}_{end}.json"

def _http_get_json(url: str) -> dict | None:
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except (URLError, HTTPError):
        return None

def fetch_nbp_rates_range(currency: str, start: str, end: str) -> list[dict]:
    # Returns list of {'effectiveDate': 'YYYY-MM-DD', 'mid': float}, sorted by date.
    cur = currency.upper()
    cp = _cache_path(cur, start, end)
    if cp.exists():
        try:
            data = json.loads(cp.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    url = f"https://api.nbp.pl/api/exchangerates/rates/a/{cur}/{start}/{end}?format=json"
    payload = _http_get_json(url)
    rates = []
    if isinstance(payload, dict):
        for it in payload.get("rates", []):
            ed = it.get("effectiveDate"); mid = it.get("mid")
            if ed and mid is not None:
                try:
                    rates.append({"effectiveDate": ed, "mid": float(mid)})
                except Exception:
                    pass
    rates.sort(key=lambda x: x["effectiveDate"])
    try:
        cp.write_text(json.dumps(rates, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return rates
