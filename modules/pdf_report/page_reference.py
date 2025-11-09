# modules/pdf_report/page_reference.py

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()


def make_reference_page(data: dict, show_period=True):
    """
    Builds per-currency FX tables.
    One currency = one table.
    """

    year_block = data["years"][0]
    fx = year_block.get("fx", {})

    elements = []

    title_style = styles["Heading2"]
    title_style.alignment = TA_CENTER

    if show_period:
        elements.append(Paragraph(f"Report period: {year_block['fromDate']} - {year_block['toDate']}", title_style))
        elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("Exchange Rates Used", title_style))
    elements.append(Spacer(1, 0.6 * cm))

    for currency, records in sorted(fx.items()):
        elements.append(Paragraph(currency, styles["Heading3"]))
        elements.append(Spacer(1, 0.2 * cm))

        table_data = [["Date", "Rate (PLN)"]]
        for r in records:
            table_data.append([r["date"], f"{r['rate']:.4f}"])

        tbl = Table(table_data, colWidths=[5.0 * cm, 5.0 * cm], hAlign="CENTER")
        tbl.setStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ])

        elements.append(tbl)
        elements.append(Spacer(1, 0.6 * cm))

    return elements

