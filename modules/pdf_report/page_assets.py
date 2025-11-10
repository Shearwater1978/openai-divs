# modules/pdf_report/page_assets.py

from reportlab.platypus import LongTable, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

from modules.money_utils import money

styles = getSampleStyleSheet()


def make_assets_page(year_block):
    """
    Build the 'Assets summary' table with automatic page breaking.
    Sorted by ticker alphabetically.
    """

    title_style = styles["Heading2"]
    title_style.alignment = TA_CENTER

    data = [["Ticker", "Currency", "Dividends (PLN)", "Taxes (PLN)", "Net (PLN)"]]

    # Build tax lookup by ticker
    tax_map = {}
    for t in year_block.get("taxes", []):
        ticker = t.get("ticker")
        if ticker:
            tax_map[ticker] = sum(money(x.get("amountPln", 0)) for x in t.get("tax", []))

    # Sort tickers alphabetically (requested behavior)
    for asset in sorted(year_block.get("dividends", []), key=lambda x: x.get("ticker", "")):

        ticker = asset.get("ticker", "UNKNOWN")
        div_records = asset.get("dividend", [])

        # Currency detection
        currency = ""
        if div_records:
            currency = (div_records[0].get("currency") or "").upper()

        # Dividends sum
        div_sum = sum(money(x.get("amountPln", 0)) for x in div_records)

        # Tax sum
        tax_sum = money(tax_map.get(ticker, 0))

        # Net = dividends + tax (tax is negative)
        net = money(div_sum + tax_sum)

        data.append([
            ticker,
            currency,
            f"{div_sum:.2f}",
            f"{tax_sum:.2f}",
            f"{net:.2f}",
        ])

    table = LongTable(data, repeatRows=1)
    table.setStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ])

    return [
        Spacer(0, 0.8 * cm),
        Paragraph("Assets Summary", title_style),
        Spacer(0, 0.3 * cm),
        table,
        Spacer(0, 1.0 * cm),
    ]
