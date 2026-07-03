import math
import random


ECONOMY_SOFT_CAP = 250_000
ECONOMY_REBASE_STEP = 120_000
ECONOMY_REBASE_MAX = 2_000_000
ECONOMY_AUTO_USER_TRIGGER = 3_500_000
ECONOMY_AUTO_GLOBAL_PEAK_TRIGGER = 8_000_000
ECONOMY_AUTO_GLOBAL_TOTAL_TRIGGER = 120_000_000
ECONOMY_AUTO_GLOBAL_OVER_CAP_TRIGGER = 12
ECONOMY_AUTO_GLOBAL_COOLDOWN_SECONDS = 43_200
ECONOMY_TAX_BRACKETS = (
    (50_000, 0.00),
    (200_000, 0.05),
    (1_000_000, 0.10),
    (5_000_000, 0.16),
    (20_000_000, 0.22),
    (None, 0.28),
)


def format_economy_amount(value):
    amount = float(value or 0)
    abs_value = abs(amount)
    if abs_value >= 100_000_000:
        return f"{amount / 100_000_000:.2f}亿"
    if abs_value >= 10_000:
        return f"{amount / 10_000:.2f}万"
    return f"{amount:.2f}"


def revalue_amount(value):
    amount = float(value or 0)
    if amount == 0:
        return 0

    sign = -1 if amount < 0 else 1
    abs_amount = abs(amount)
    if abs_amount <= ECONOMY_SOFT_CAP:
        return int(round(amount))

    compressed = ECONOMY_SOFT_CAP + math.log10(abs_amount / ECONOMY_SOFT_CAP) * ECONOMY_REBASE_STEP
    compressed = min(ECONOMY_REBASE_MAX, compressed)
    return int(round(compressed)) * sign


def _calculate_progressive_tax(current_balance, raw_gain):
    safe_balance = max(0, int(round(float(current_balance or 0))))
    safe_gain = max(0, int(round(float(raw_gain or 0))))
    if safe_gain <= 0:
        return 0

    remaining_gain = safe_gain
    cursor_balance = safe_balance
    tax_total = 0

    for upper_bound, tax_rate in ECONOMY_TAX_BRACKETS:
        if remaining_gain <= 0:
            break

        if upper_bound is None:
            taxable_chunk = remaining_gain
        else:
            if cursor_balance >= upper_bound:
                continue
            taxable_chunk = min(remaining_gain, upper_bound - cursor_balance)

        if taxable_chunk <= 0:
            continue

        tax_total += int(round(taxable_chunk * tax_rate))
        remaining_gain -= taxable_chunk
        cursor_balance += taxable_chunk

    return min(safe_gain, max(0, tax_total))


def calculate_progressive_gain(current_balance, raw_gain):
    safe_gain = max(0, int(round(float(raw_gain or 0))))
    if safe_gain <= 0:
        return 0
    tax_total = _calculate_progressive_tax(current_balance, safe_gain)
    return max(1, safe_gain - tax_total)


def build_economy_delta_summary(current_balance, raw_delta, applied_delta):
    raw_int = int(round(float(raw_delta or 0)))
    applied_int = int(round(float(applied_delta or 0)))
    tax_amount = raw_int - applied_int if raw_int > 0 else 0
    effective_tax_rate = (tax_amount / raw_int) if raw_int > 0 else 0.0
    return {
        "before_balance": int(round(float(current_balance or 0))),
        "raw_delta": raw_int,
        "applied_delta": applied_int,
        "tax_amount": tax_amount,
        "effective_tax_rate": effective_tax_rate,
        "after_balance": int(round(float(current_balance or 0))) + applied_int,
    }


def random_economy_flavor(summary):
    if not summary or summary["raw_delta"] <= 0 or summary["tax_amount"] <= 0:
        return "镇会计喵已经帮你按新币制记账。"

    candidates = [
        f"镇长路过顺爪抽走了 **{summary['tax_amount']}** 喵币，说这是阶梯猫砂税。",
        f"财政喵按了半天算盘，代你上缴了 **{summary['tax_amount']}** 喵币的分段税。",
        f"税务橘猫把 **{summary['tax_amount']}** 喵币叼回了镇公所，嘴里还念叨着高收入喵要多担待。",
        f"黑箱预算突然启动，系统按阶梯税率拨走了 **{summary['tax_amount']}** 喵币去修补镇长办公室沙发。",
        f"会计喵眯着眼盖章：本次按分段税率代扣 **{summary['tax_amount']}** 喵币，钱包依旧够你继续折腾。",
    ]
    return random.choice(candidates)


def format_economy_notice(summary):
    if not summary:
        return ""
    guard_notice = format_economy_guard_notice(summary.get("auto_rebase_events"))
    if summary["raw_delta"] <= 0:
        base_notice = "喵喵财政局已按新币制登记本次支出。"
        return f"{base_notice}\n{guard_notice}" if guard_notice else base_notice
    if summary["tax_amount"] <= 0:
        base_notice = "本次收益已通过新币制审查，完整入账。"
        return f"{base_notice}\n{guard_notice}" if guard_notice else base_notice
    base_notice = (
        f"原始收益 **{format_economy_amount(summary['raw_delta'])}**，"
        f"实收 **{format_economy_amount(summary['applied_delta'])}**，"
        f"本次综合税率 **{summary['effective_tax_rate'] * 100:.1f}%**。\n"
        f"{random_economy_flavor(summary)}"
    )
    return f"{base_notice}\n{guard_notice}" if guard_notice else base_notice


def format_economy_guard_notice(events):
    if not events:
        return ""

    lines = []
    for event in events:
        if event.get("trigger_kind") == "auto_personal":
            lines.append(
                "🚨 财政喵发现你的钱包鼓得像气球，紧急启动个人资产熔断："
                f" **{format_economy_amount(event['total_before'])}** → **{format_economy_amount(event['total_after'])}**。"
            )
        elif event.get("trigger_kind") == "auto_global":
            lines.append(
                "🌐 镇政厅拉响了全服通胀警报，自动缩表已完成："
                f" **{format_economy_amount(event['total_before'])}** → **{format_economy_amount(event['total_after'])}**。"
            )
    return "\n".join(lines)


def describe_revalue(before_value):
    after_value = revalue_amount(before_value)
    delta = after_value - int(round(float(before_value or 0)))
    return {
        "before": int(round(float(before_value or 0))),
        "after": after_value,
        "delta": delta,
    }


__all__ = [
    "ECONOMY_REBASE_MAX",
    "ECONOMY_REBASE_STEP",
    "ECONOMY_SOFT_CAP",
    "ECONOMY_AUTO_GLOBAL_COOLDOWN_SECONDS",
    "ECONOMY_AUTO_GLOBAL_OVER_CAP_TRIGGER",
    "ECONOMY_AUTO_GLOBAL_PEAK_TRIGGER",
    "ECONOMY_AUTO_GLOBAL_TOTAL_TRIGGER",
    "ECONOMY_AUTO_USER_TRIGGER",
    "ECONOMY_TAX_BRACKETS",
    "build_economy_delta_summary",
    "calculate_progressive_gain",
    "describe_revalue",
    "format_economy_amount",
    "format_economy_guard_notice",
    "format_economy_notice",
    "random_economy_flavor",
    "revalue_amount",
]
