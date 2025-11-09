from modules.dividend_processor import process_dividend_line

def test_process_dividend_line_ok():
    fx = {"USD": [{"date": "2025-01-02", "rate": 4.10}]}
    line = 'Dividends,Data,USD,2025-01-02,AGR(US...) Cash Dividend,4.4'
    rec = process_dividend_line(line, fx, "2025")
    assert rec["ticker"] == "AGR"
    assert rec["amount"] == 4.4
    assert rec["amountPln"] == 18.04
