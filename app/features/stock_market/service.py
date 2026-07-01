def parse_positive_int(value):
    if not value.isdigit():
        raise ValueError("not a positive integer")
    amount = int(value)
    if amount <= 0:
        raise ValueError("not a positive integer")
    return amount


def parse_positive_amount(value):
    amount = round(float(value), 2)
    if amount <= 0:
        raise ValueError("not a positive amount")
    return amount


def format_market_trend(price, change):
    if change > 0:
        trend = f"🔼 +{change:.2f}"
    elif change < 0:
        trend = f"🔽 {change:.2f}"
    else:
        trend = "⏺️ 0.00"
    pct = (change / (price - change)) * 100 if (price - change) != 0 else 0
    return trend, pct


def summarize_portfolio(cash, loan, positions):
    total_assets = cash - loan
    content = f"💰 现金: {cash:.2f}\n💸 贷款: {loan:.2f}\n\n**持仓:**\n"
    if not positions:
        return total_assets, content + "无"

    lines = []
    for stock_id, quantity, price in positions:
        value = price * quantity
        total_assets += value
        lines.append(f"{stock_id}: {quantity}股 (≈{value:.2f})")
    return total_assets, content + "\n".join(lines)


__all__ = [
    "format_market_trend",
    "parse_positive_amount",
    "parse_positive_int",
    "summarize_portfolio",
]
