import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, PageBreak, Spacer, Paragraph

from modules.logger_module import get_logger
from modules.money_utils import money
from modules.pdf_report.font_utils import register_fonts, make_styles
from modules.pdf_report.page_assets import make_assets_page
from modules.pdf_report.page_monthly_summary import make_monthly_summary_page
# Важно: мы договорились БОЛЬШЕ НЕ ПОКАЗЫВАТЬ страницы с курсами в PDF.

logger = get_logger("annual_pdf_builder")


def _normalize_period(year_block: dict):
    dates = []
    for dblk in year_block.get("dividends", []) or []:
        for rec in dblk.get("dividend", []) or []:
            if rec.get("date"):
                dates.append(rec["date"])
    for tblk in year_block.get("taxes", []) or []:
        for rec in tblk.get("tax", []) or []:
            if rec.get("date"):
                dates.append(rec["date"])
    if dates:
        year_block["fromDate"] = min(dates)
        year_block["toDate"] = max(dates)
    else:
        y = str(year_block.get("year", ""))
        if y.isdigit() and len(y) == 4:
            year_block["fromDate"] = f"{y}-01-01"
            year_block["toDate"] = f"{y}-12-31"


def _aggregate_year(year_block: dict):
    total_div_pln = 0.0
    total_tax_pln = 0.0
    tickers = set()
    div_count = 0
    tax_count = 0
    per_ccy_pln = {}

    for dblk in year_block.get("dividends", []) or []:
        ticker = dblk.get("ticker", "UNKNOWN")
        tickers.add(ticker)
        for rec in dblk.get("dividend", []) or []:
            div_count += 1
            v = float(rec.get("amountPln", 0) or 0)
            total_div_pln += v
            ccy = (rec.get("currency") or "").upper()
            if ccy:
                per_ccy_pln[ccy] = per_ccy_pln.get(ccy, 0.0) + v

    for tblk in year_block.get("taxes", []) or []:
        ticker = tblk.get("ticker", "UNKNOWN")
        tickers.add(ticker)
        for rec in tblk.get("tax", []) or []:
            tax_count += 1
            v = float(rec.get("amountPln", 0) or 0)
            total_tax_pln += v
            ccy = (rec.get("currency") or "").upper()
            if ccy:
                per_ccy_pln[ccy] = per_ccy_pln.get(ccy, 0.0) + v

    total_div_pln = money(total_div_pln)
    total_tax_pln = money(total_tax_pln)
    add_pl_tax = money(total_div_pln * 0.09)
    final_net = money(total_div_pln + total_tax_pln - add_pl_tax)
    per_ccy_pln = {k: money(v) for k, v in per_ccy_pln.items()}

    return {
        "total_div_pln": total_div_pln,
        "total_tax_pln": total_tax_pln,
        "add_pl_tax": add_pl_tax,
        "final_net": final_net,
        "tickers_count": len([t for t in tickers if t and t != "UNKNOWN"]),
        "div_count": div_count,
        "tax_count": tax_count,
        "per_ccy_pln": per_ccy_pln,
    }


def _make_cover(year_block: dict, styles):
    return [
        Paragraph(f"Tax report — {year_block.get('year','----')}", styles["TitleCenter"]),
        Spacer(1, 0.8 * cm),
        Paragraph(
            f"Report period: {year_block.get('fromDate','---')} - {year_block.get('toDate','---')}",
            styles["H3Center"],
        ),
        Spacer(1, 0.8 * cm),
    ]


def _make_summary(year_block: dict, styles):
    stats = _aggregate_year(year_block)

    # Таблица итогов
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    totals_header = ["Metric", "Amount (PLN)"]
    totals_rows = [
        ["Total Dividends", f"{stats['total_div_pln']:.2f}"],
        ["Withheld Tax (sum)", f"{stats['total_tax_pln']:.2f}"],
        ["Additional Tax (PL, 9%)", f"{stats['add_pl_tax']:.2f}"],
        ["Final Net (after full 19%)", f"{stats['final_net']:.2f}"],
    ]
    t1 = Table([totals_header] + totals_rows, hAlign="CENTER", colWidths=[9.0 * cm, 7.0 * cm])
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    # Диагностика
    diag_header = ["Indicator", "Value"]
    diag_rows = [
        ["Tickers (unique)", str(stats["tickers_count"])],
        ["Dividend rows", str(stats["div_count"])],
        ["Tax rows", str(stats["tax_count"])],
    ]
    t2 = Table([diag_header] + diag_rows, hAlign="CENTER", colWidths=[9.0 * cm, 7.0 * cm])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    elements = [
        Paragraph("Yearly Summary", styles["TitleCenter"]),
        Spacer(1, 0.6 * cm),
        t1,
        Spacer(1, 0.8 * cm),
        Paragraph("Diagnostics", styles["H4Center"]),
        Spacer(1, 0.2 * cm),
        t2,
    ]

    # По-валютные суммы (в PLN), если есть
    if stats["per_ccy_pln"]:
        ccy_header = ["Currency", "PLN total"]
        ccy_rows = [[ccy, f"{amt:.2f}"] for ccy, amt in sorted(stats["per_ccy_pln"].items())]
        t3 = Table([ccy_header] + ccy_rows, hAlign="CENTER", colWidths=[8.0 * cm, 8.0 * cm])
        t3.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("BOX", (0, 0), (-1, -1), 1, colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements += [
            Spacer(1, 0.8 * cm),
            Paragraph("Per-currency totals (PLN)", styles["H4Center"]),
            Spacer(1, 0.2 * cm),
            t3,
        ]

    return elements


def _make_pit38_page(year_block: dict, styles):
    from reportlab.platypus import Table, TableStyle, Spacer, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from modules.money_utils import money

    stats = _aggregate_year(year_block)

    # PIT-38 logic:
    przychod = stats["total_div_pln"]
    podatek_19 = money(przychod * 0.19)
    zaplacony_uzrodla = abs(stats["total_tax_pln"])
    doplata = money(podatek_19 - zaplacony_uzrodla)

    rows = [
        ["Wyszczególnienie", "Kwota (PLN)"],
        ["Przychód z dywidend", f"{przychod:.2f}"],
        ["Podatek należny w Polsce (19%)", f"{podatek_19:.2f}"],
        ["Zapłacony u źródła (10%)", f"-{zaplacony_uzrodla:.2f}"],
        ["Do dopłaty w PIT-38", f"{doplata:.2f}"],
    ]

    tbl = Table(rows, colWidths=[10*cm, 6*cm], hAlign="CENTER")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTNAME", (0,0), (-1,-1), "DejaVuSans"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    return [
        Paragraph("PIT-38 — Podsumowanie", styles["H2Center"]),
        Spacer(1, 0.4 * cm),
        tbl,
    ]


def build_yearly_pdf_from_json(json_path: str, output_path: str):
    # 1) шрифт + стили
    font_name = register_fonts("fonts/DejaVuSans.ttf", "DejaVuSans")
    styles = make_styles(font_name)

    # 2) читаем JSON и нормализуем период
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to read JSON {json_path}: {e}")
        return

    years = data.get("years") or []
    if not years:
        logger.error(f"No year blocks in JSON: {json_path}")
        return

    year_block = years[0]
    _normalize_period(year_block)

    # 3) документ
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )

    elements = []
    # Cover
    elements += _make_cover(year_block, styles)
    elements.append(PageBreak())
    # Assets (таблица может растягиваться на много страниц)
    # elements += make_assets_page({"years": [year_block]}, styles)
    elements += make_assets_page(year_block)
    elements.append(PageBreak())
    # Monthly summary
    elements += make_monthly_summary_page({"years": [year_block]}, styles)
    elements.append(PageBreak())
    # Yearly summary
    elements += _make_summary(year_block, styles)

    elements.append(PageBreak())
    elements += _make_pit38_page(year_block, styles)


    try:
        doc.build(elements)
        logger.info(f"Yearly PDF built: {output_path}")
    except Exception as e:
        logger.error(f"Failed to build yearly PDF: {e}")

