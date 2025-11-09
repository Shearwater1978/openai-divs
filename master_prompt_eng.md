
# MASTER PROMPT (English)

Create a Python project that processes Interactive Brokers MTM Summary CSV reports and generates a consolidated yearly report in **JSON** and **PDF** formats.

This specification must always remain the **source of truth** for implementation.

---

## 1. Input Data

### Source
One or multiple **Interactive Brokers MTM Summary CSV** statements.

### Notes
- Files **may contain a UTF‑8 BOM** — BOM must be detected and removed.
- The CSV format uses English month names and localized date fields.

### Period Line Format Example
```
Statement,Data,Period,"January 1, 2025 - January 31, 2025"
```

### Required Extraction
| Field | Output Value | Example |
|------|--------------|---------|
| `fromDate` | Start date normalized to `YYYY-MM-DD` | `2025-01-01` |
| `toDate` | End date normalized to `YYYY-MM-DD` | `2025-01-31` |
| `year` | Always use the **right-side date** of the period | `2025` |

---

## 2. Dividend Parsing

### Row Pattern
```
Dividends,Data,<CURRENCY>,<DATE>,<DESCRIPTION>,<AMOUNT>
```

### Ticker Extraction Rule
Ticker is the text before `(`:
```
AGR(US05351W1036) Cash Dividend → AGR
```

### Store Each Dividend in JSON as:
```json
{
  "ticker": "AGR",
  "currency": "USD",
  "date": "2025-01-02",
  "amount": 4.40,
  "amountPln": 18.04
}
```

### Filtering
Ignore rows where `date` **does not match report year**.

---

## 3. Withholding Tax Parsing

### Row Pattern
```
Withholding Tax,Data,<CURRENCY>,<DATE>,<DESCRIPTION>,<AMOUNT>
```

### Rules
- Ticker extraction = same as dividends.
- Convert to PLN using FX rate.
- Do **not** flip sign — store value exactly as provided.

---

## 4. Currency Conversion (NBP API)

Fetch conversion rates using:
```
https://api.nbp.pl/api/exchangerates/rates/a/<CURRENCY>/<FROM>/<TO>?format=json
```

### Requirements
- Use **table A** rates.
- If currency is `PLN` → rate = `1.0`.
- **Cache responses** on disk under `cache/nbp/`.

### JSON Storage Format (`fx`)
```json
"fx": [
  {"currency": "USD", "date": "2025-01-02", "rate": 4.10}
]
```

---

## 5. Rounding

Use **banker's rounding (half-even)** to 2 decimals.

| Input | Output |
|-------|--------|
| `2.345` | `2.34` |
| `2.355` | `2.36` |

Function name: `money(value: float) -> float`

---

## 6. JSON Output Structure

```json
{
  "years": [
    {
      "year": "2025",
      "fromDate": "2025-01-02",
      "toDate": "2025-03-31",
      "dividends": [
        {
          "ticker": "AGR",
          "currency": "USD",
          "dividend": [
            {"date": "2025-01-02", "amount": 4.40, "amountPln": 18.04}
          ]
        }
      ],
      "taxes": [
        {
          "ticker": "AGR",
          "currency": "USD",
          "tax": [
            {"date": "2025-01-02", "amount": -1.10, "amountPln": -4.40}
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

---

## 7. PDF Output Requirements

Use **reportlab.platypus** and automatically paginate tables.

### PDF Section Order
1. **Cover page** (Report period centered)
2. **Assets Summary** (multi-page table allowed)
3. **Monthly Summary**
4. **Yearly Summary**:
   - Totals Summary (centered)
   - Diagnostics (centered)
   - Final Net (PL tax adjustment logic included)

### Assets Summary Table Columns
| Ticker | Currency | Div (PLN) | Tax (PLN) | Net (PLN) |

### Monthly Summary Table
| Month | Div PLN | Tax PLN | Net PLN |

---

## 8. Polish PIT-38 Calculation Rule

Additional 9% tax must be applied:
```
additional_pl_tax = total_dividends_pln * 0.09
final_net = total_dividends_pln + total_tax_pln - additional_pl_tax
```

Display these clearly in Yearly Summary.

---

## 9. Test Suite Requirements (pytest)

Tests must validate:

| Area | Requirements |
|------|-------------|
| Date Parsing | BOM removal, month mapping, full range extraction |
| Dividend Parsing | Ticker extraction, year filtering |
| Tax Parsing | Negative values handling |
| FX Conversion | Caching, correct fallback behavior |
| money() | Correct half-even rounding |
| Grouping | add_dividend_to_report and add_tax_to_report accumulate correctly |
| PDF Generation | Multi-page tables render without layout collapse |

---

## 10. Implementation Stability

This prompt defines the **expected final state** of the project.
All future adjustments must remain consistent with this specification.


