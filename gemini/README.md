# 🚀 IBKR PIT-38 Analyzer: Multi-Account Tax Engine

This Python project automates the processing of Interactive Brokers (IBKR) client activity statements to generate tax-compliant reports for the Polish PIT-38 declaration. It is designed to handle complex scenarios involving asset migration and currency conversion rules.

**Key Features:**

* **PIT-38 Compliance:** Currency conversion using the NBP **T-1 Business Day** rule.
* **Multi-Account History:** Resolution of asset transfers (FOP/ACATS) to maintain continuous Cost Basis (FIFO).
* **Dual Output:** Generation of a queryable JSON data store and a formatted PDF report.

## 🛠️ Project Architecture (src/)

| Module | Role | Status |
| :--- | :--- | :--- |
| `main.py` | **The core orchestrator.** Scans input files, defines the reporting period, and coordinates module execution. | Defined |
| `parser.py` | Reads and segments the raw IBKR CSV Activity Statement, and auto-detects foreign currencies. | Defined |
| `data_merger.py` | Unifies history from multiple accounts, resolving position transfers to maintain continuous Cost Basis. | Defined |
| `forex_nbp_api.py` | Fetches bulk PLN exchange rates from the NBP API and provides the compliant **T-1 Business Day** lookup logic. | Defined |
| `tax_engine.py` | Applies FIFO rules, performs all currency conversions to PLN, and calculates the final realized P&L. | Defined |
| `json_exporter.py` | Saves the entire "Golden Dataset" (all processed data) into a JSON file for flexible analysis. | Defined |
| `pdf_generator.py` | Creates the final multi-page, formatted PDF report. | Defined |

---

## 💻 Setup and Dependencies

### 1. Installation

This project requires Python 3.9+ and the following libraries:

### `requirements.txt`

```text
# Data handling and analysis
pandas

# API requests
requests

# Date/Time and Holiday handling (Crucial for T-1 NBP rule)
holidays

# PDF generation
fpdf2 
matplotlib # For generating charts in the PDF report (e.g., monthly yield)

Installation Command: pip install -r requirements.txt

2. File Preparation
Create two directories in the project root: data/ and output/.

Place all required IBKR Activity Statement CSV files into the data/ directory.

📋 Obtaining Required Reports
The system requires IBKR Activity Statements in CSV format, typically generated via the Flex Query tool in the IBKR Client Portal.

Activity Statement for Monthly Processing: Must include Trades, Dividends, Withholding Tax, Cash Report, and Transfers.

Historical Data for Account Migration: Obtain the full historical report from the old account before asset migration to preserve the original Cost Basis.

⚙️ Running the Project
1. Standard Monthly Run
The main.py script automatically determines the previous calendar month as the reporting period.

Bash

python main.py
Output: The generated files will be saved in the output/ directory.

pit38_data_[YEAR].json (Full data store)

pit38_report_[YEAR].pdf (Formatted report)

2. Running Unit Tests
To ensure the accuracy of the critical conversion and FIFO logic, run the unit tests before each major calculation or deployment.

Bash

# Run all tests in the tests/ directory
python -m unittest discover tests
💡 Module Usage: parser.py (Multi-File Handling)
The parser.py module processes one CSV file at a time. The responsibility for iterating over multiple accounts or monthly reports lies with main.py, which scans the data/ directory and passes the results to the data_merger.py for final consolidation.