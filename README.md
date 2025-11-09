# IBKR Dividend & Tax Report (Poland, PIT-38)

This project processes Interactive Brokers monthly statements (MTM Summary CSV), aggregates dividends and withholding taxes for a selected year, converts amounts to PLN using historical NBP FX rates, and generates a JSON dataset and a PIT-38-ready PDF report.

## Features

| Feature | Description |
|--------|-------------|
| Automatic processing of multiple CSV reports | Place all reports in `broker_reports/` and run once |
| Robust period detection | Parses `Statement,Data,Period,"January 1, 2025 - January 31, 2025"` format |
| Historical FX conversion (NBP) | API retrieval + caching in `cache/` |
| Ticker identification | Extracted from patterns like `AAPL(US0378331005) ...` |
| PDF ready for PIT‑38 | Contains yearly totals, monthly summary, and asset breakdown |
| Proper financial rounding | Banker's rounding (half-even) for 2 decimals |

---

## Project Structure

```
project/
 ├─ main.py
 ├─ broker_reports/          # Drop IBKR CSV files here
 ├─ tax_reports/             # Output JSON + PDF
 ├─ modules/
 │   ├─ date_parser.py
 │   ├─ dividend_processor.py
 │   ├─ tax_processor.py
 │   ├─ nbp.py
 │   ├─ money_utils.py
 │   └─ pdf_report/
 │       ├─ annual_builder.py
 │       ├─ page_assets.py
 │       └─ page_monthly_summary.py
 └─ README.md
```

---

## Usage

### Step 1 — Put IBKR CSV files in:

```
broker_reports/
```

### Step 2 — Generate a yearly report:

```bash
python main.py --year 2025
```

### Output:

```
tax_reports/divs_2025.json
tax_reports/report_2025_full.pdf
```

---

## JSON Output Format

```json
{
  "years": [
    {
      "year": "2025",
      "fromDate": "2025-01-01",
      "toDate": "2025-12-31",
      "dividends": [
        {
          "ticker": "AGR",
          "currency": "USD",
          "dividend": [
            {"date": "2025-01-02", "amount": 4.4, "amountPln": 18.04}
          ]
        }
      ],
      "taxes": [
        {
          "ticker": "AGR",
          "currency": "USD",
          "tax": [
            {"date": "2025-01-02", "amount": -0.44, "amountPln": -1.80}
          ]
        }
      ],
      "fx": [
        {"currency": "USD", "date": "2025-01-02", "rate": 4.10}
      ]
    }
  ]
}
```

Note: **`fx` replaces old `rates` key.**

---

## PDF Contents

1. Cover Page
2. **Assets Summary** (ticker → dividends, taxes, net)
3. **Monthly Summary** (January → December breakdown)
4. **Yearly Summary (PIT‑38)**:
   - Sum of dividends
   - Withheld tax (foreign)
   - Additional Polish tax (to reach 19%)
   - Final net

**FX tables are no longer included in the PDF** — data remains in JSON.

---

## Tax Logic (Poland PIT‑38)

| Description | Rate |
|------------|------|
| U.S. withholding | **10%** |
| Required Polish tax | **19%** |
| Additional tax due in PL | **9%** when U.S. tax already paid |

```
PL_tax_due = (sum_div_pln * 0.19) - withheld_tax_pln
```

---

## Rounding (money())

Banker's rounding (half-even):

| Input | Result |
|-------|--------|
| 2.345 | 2.34 |
| 2.355 | 2.36 |

---

## Tests (pytest)

Covers:
- date parsing
- dividend/tax grouping
- FX retrieval & caching
- financial rounding
- PDF table data correctness

---

## License

MIT
