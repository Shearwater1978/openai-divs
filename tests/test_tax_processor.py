from modules.tax_processor import process_tax_line

def test_process_tax_line_ok():
    fx = {"USD": [{"date": "2025-01-02", "rate": 4.10}]}
    line = 'Withholding Tax,Data,USD,2025-01-02,AGR(US...) Cash Dividend,-2.12'
    rec = process_tax_line(line, fx, "2025")
    assert rec["ticker"] == "AGR"
    assert rec["amount"] == -2.12
    assert rec["amountPln"] == -8.69
