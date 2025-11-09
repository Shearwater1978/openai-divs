from reportlab.platypus import LongTable, Paragraph, Spacer, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from modules.money_utils import money


def make_assets_page(ctx, styles):
    year_block = ctx.get("years", [])[0]

    data = [["Ticker", "Currency", "Dividends (PLN)", "Tax (PLN)", "Net (PLN)"]]

    # Собираем налоги по тикеру
    tax_by_ticker = {}
    for t in year_block.get("taxes", []):
        tkr = t.get("ticker")
        if tkr:
            tax_by_ticker[tkr] = sum(money(x.get("amountPln", 0)) for x in t.get("tax", []))

    # Строки по дивидендам
    for d in year_block.get("dividends", []):
        ticker = d.get("ticker", "UNKNOWN")
        recs = d.get("dividend", []) or []
        currency = (recs[0].get("currency") or "").upper() if recs else ""
        div_sum = sum(money(x.get("amountPln", 0)) for x in recs)
        tax_sum = money(tax_by_ticker.get(ticker, 0.0))
        net = money(div_sum + tax_sum)
        data.append([ticker, currency, f"{div_sum:.2f}", f"{tax_sum:.2f}", f"{net:.2f}"])

    table = LongTable(data, repeatRows=1, colWidths=[4.0*cm, 3.0*cm, 4.0*cm, 3.5*cm, 3.5*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
    ]))

    return [
        Paragraph("Assets Summary", styles["H2Center"]),
        Spacer(1, 0.5 * cm),
        table,
    ]

