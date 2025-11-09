import json
from unittest.mock import patch
from modules.nbp import fetch_nbp_rates_range

@patch("modules.nbp.urlopen")
def test_fetch_nbp_rates_range_uses_http_and_cache(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
        "rates": [
            {"effectiveDate": "2025-01-02", "mid": 4.10},
            {"effectiveDate": "2025-01-03", "mid": 4.12},
        ]
    }).encode("utf-8")

    rates = fetch_nbp_rates_range("USD", "2025-01-01", "2025-01-31")
    assert isinstance(rates, list)
    assert len(rates) == 2
    assert rates[0]["mid"] == 4.10

    # Second call should hit cache → urlopen not called again
    fetch_nbp_rates_range("USD", "2025-01-01", "2025-01-31")
    mock_urlopen.assert_called_once()
