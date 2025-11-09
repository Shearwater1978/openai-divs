
# IBKR Dividend & Tax Report Generator

This tool converts Interactive Brokers MTM Summary CSV files into a structured yearly tax report.

### Features
- Multi-file yearly aggregation
- Accurate FX conversion via NBP API (cached)
- Full PDF report with assets, monthly totals, and PIT-38 assistance

### Requirements
```
python >= 3.10
pip install -r requirements.txt
```

### Generate Yearly Report
```
python main.py --year 2025
```

### Output
- JSON → `tax_reports/divs_2025.json`
- PDF → `tax_reports/report_2025_full.pdf`
