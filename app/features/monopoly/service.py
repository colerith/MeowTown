def build_status_text(status, turns, fixed_roll, luck):
    status_text = "🟢 自由行动" if status == "normal" else f"🔒 禁闭中 ({turns}回合)"
    if fixed_roll > 0:
        status_text += f" | 🎲 骰子锁定: {fixed_roll}"
    if luck > 0:
        status_text += f" | 🌩️ 霉运值: {luck}/3"
    return status_text


def calculate_upgrade_cost(price):
    return round(price * 0.5, 2)


def calculate_property_rent(tile, level, effect):
    return round(tile["rent"][level - 1] * (2 if effect == "roadblock" else 1), 2)


def handle_bad_luck_after_event(current_bad_luck, event_is_bad):
    return current_bad_luck + 1 if event_is_bad else 0


__all__ = [
    "build_status_text",
    "calculate_property_rent",
    "calculate_upgrade_cost",
    "handle_bad_luck_after_event",
]
