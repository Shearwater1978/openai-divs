import argparse
from pathlib import Path
from datetime import datetime
import json
from modules.logger_module import get_logger
from modules.date_parser import parse_report_period
from modules.dividend_processor import process_dividend_line, add_dividend_to_report
from modules.tax_processor import process_tax_line, add_tax_to_report
from modules.nbp import fetch_nbp_rates_range

logger = get_logger("main")

def _merge_fx(yb_fx: dict, ccy: str, nbp_list: list[dict]):
    arr = yb_fx.setdefault(ccy, [])
    for it in nbp_list:
        rec = {"date": it["effectiveDate"], "rate": float(it["mid"])}
        if not any(r.get("date") == rec["date"] for r in arr):
            arr.append(rec)
    arr.sort(key=lambda x: x["date"])

def process_broker_report(file_path: str, report_data: dict, target_year: str | None = None):
    lines = Path(file_path).read_text(encoding="utf-8-sig").splitlines()
    info = parse_report_period(file_path, lines)
    if not info:
        logger.warning(f"Could not parse report period for: {file_path}")
        return
    year = info["year"]
    years = report_data.setdefault("years", [])
    yb = next((y for y in years if y.get("year") == year), None)
    if not yb:
        yb = {"year": year, "fromDate": info["fromDate"], "toDate": info["toDate"], "dividends": [], "taxes": [], "fx": {}}
        years.append(yb)

    # collect currencies & min/max dates
    ccys=set(); min_d=None; max_d=None
    for raw in lines:
        if raw.startswith(("Dividends,Data,","Withholding Tax,Data,")):
            parts=[p.strip().strip('"') for p in raw.split(",")]
            if len(parts)<6: continue
            ccy=parts[2].upper(); date=parts[3]
            if target_year and not date.startswith(target_year): continue
            ccys.add(ccy)
            try:
                d = datetime.strptime(date, "%Y-%m-%d").date()
                min_d = d if min_d is None or d<min_d else min_d
                max_d = d if max_d is None or d>max_d else max_d
            except Exception:
                pass

    # fetch & merge fx
    if ccys and min_d and max_d:
        start=min_d.strftime("%Y-%m-%d"); end=max_d.strftime("%Y-%m-%d")
        for c in sorted(ccys):
            if c=="PLN":
                _merge_fx(yb["fx"], c, [{"effectiveDate": start, "mid": 1.0}])
            else:
                _merge_fx(yb["fx"], c, fetch_nbp_rates_range(c, start, end))

    # parse rows
    for raw in lines:
        if raw.startswith("Dividends,Data,"):
            rec = process_dividend_line(raw, yb["fx"], year)
            if rec and (not target_year or rec["date"].startswith(target_year)):
                add_dividend_to_report(report_data, year, rec)
        elif raw.startswith("Withholding Tax,Data,"):
            rec = process_tax_line(raw, yb["fx"], year)
            if rec and (not target_year or rec["date"].startswith(target_year)):
                add_tax_to_report(report_data, year, rec)

def process_all_reports(folder: str, target_year: str | None = None) -> dict:
    data={"years": []}
    for p in sorted(Path(folder).glob("*.csv")):
        logger.info(f"Processing {p.name}")
        process_broker_report(str(p), data, target_year)
    return data

def save_json(report_data: dict, out_dir: str, year: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / f"divs_{year}.json"
    path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved JSON: {path}")
    return str(path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="Path to single CSV report (optional)")
    ap.add_argument("--year", help="Collect all reports from broker_reports/ for year", type=str)
    args = ap.parse_args()

    if args.year:
        data = process_all_reports("broker_reports", args.year)
        if not data.get("years"): 
            logger.info("No data found for given year"); return
        y = data["years"][0]["year"]
        json_path = save_json(data, "tax_reports", y)
        from modules.pdf_report.annual_builder import build_yearly_pdf_from_json
        build_yearly_pdf_from_json(json_path, f"tax_reports/report_{y}_full.pdf")
        return

    if not args.file:
        logger.error("No input file. Use: python main.py <file.csv> or --year <YYYY>")
        return

    data = {"years": []}
    process_broker_report(args.file, data, None)
    if not data.get("years"):
        logger.info("No data collected from file"); return
    y = data["years"][0]["year"]
    json_path = save_json(data, "tax_reports", y)
    from modules.pdf_report.annual_builder import build_yearly_pdf_from_json
    build_yearly_pdf_from_json(json_path, f"tax_reports/report_{y}.pdf")

if __name__ == "__main__":
    main()
