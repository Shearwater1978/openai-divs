# tests/test_rates.py
import json
from unittest.mock import patch
from pathlib import Path
import modules.nbp as nbp


@patch("modules.nbp.urllib.request.urlopen")
def test_fetch_nbp_rates_range_uses_http_and_cache(mock_urlopen, tmp_path, monkeypatch):
    # изолируем кэш в temp каталоге, чтобы не было попаданий в старый кэш
    new_cache = tmp_path / "nbp_cache"
    new_cache.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(nbp, "CACHE_DIR", new_cache)

    # мок HTTP-ответа NBP (RAW формат)
    mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
        "rates": [
            {"effectiveDate": "2025-01-02", "mid": 4.10},
            {"effectiveDate": "2025-01-03", "mid": 4.12},
        ]
    }).encode("utf-8")

    # 1-й вызов → должен сходить в HTTP
    rates = nbp.fetch_nbp_rates_range("USD", "2025-01-01", "2025-01-31")
    assert isinstance(rates, list)
    assert len(rates) == 2
    assert rates[0]["effectiveDate"] == "2025-01-02"
    assert rates[0]["mid"] == 4.10

    # убедимся, что кэш-файл создан
    cache_file = new_cache / "USD_2025-01-01_2025-01-31.json"
    assert cache_file.exists()

    # 2-й вызов → должен брать из кэша, новых HTTP-вызовов не должно быть
    rates2 = nbp.fetch_nbp_rates_range("USD", "2025-01-01", "2025-01-31")
    assert rates2 == rates
    mock_urlopen.assert_called_once()
