from decimal import Decimal, ROUND_HALF_EVEN

def money(value) -> float:
    # Round to two decimals with bankers' rounding (half-even).
    q = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return float(q)
