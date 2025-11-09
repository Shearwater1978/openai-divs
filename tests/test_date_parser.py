from modules.date_parser import parse_report_period

def test_parse_report_period_basic():
    lines = [
        'Statement,Header,Field Name,Field Value',
        'Statement,Data,Title,MTM Summary',
        'Statement,Data,Period,"January 1, 2025 - January 31, 2025"',
    ]
    info = parse_report_period("dummy.csv", lines)
    assert info is not None
    assert info["fromDate"] == "2025-01-01"
    assert info["toDate"] == "2025-01-31"
    assert info["year"] == "2025"
