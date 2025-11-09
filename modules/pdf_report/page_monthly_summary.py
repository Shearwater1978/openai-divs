from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm


def make_monthly_summary_page(ctx, styles):
    year_block = ctx.get("years", [])[0]

    from collections import defaultdict
    div_m = defaultdict(float)
    tax_m = defaultdict(float)

    def month_key(d):
        return d[:7] if d else "unknown"

    for a in year_block.get("dividends", []) or []:
        for r in a.get("dividend", []) or []:
            div_m[month_key(r.get("date"))] += float(r.get("amountPln", 0) or 0)

    for a in year_block.get("taxes", []) or []:
        for r in a.get("tax", []) or []:
            tax_m[month_key(r.get("date"))] += float(r.get("amountPln", 0) or 0)

    months = sorted(set(div_m) | set(tax_m))
    rows = [["Month", "Dividends (PLN)", "Tax (PLN)"]]
    for m in months:
        rows.append([m, f"{div_m[m]:.2f}", f"{tax_m[m]:.2f}"])

    tbl = Table(rows, hAlign="CENTER", colWidths=[6.0 * cm, 5.0 * cm, 5.0 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
    ]))

    return [
        Paragraph("Monthly Summary", styles["H2Center"]),
        Spacer(1, 0.3 * cm),
        tbl,
    ]

