from rest_framework.exceptions import ValidationError

MAX_STOCK_QTY = 1_000_000
MAX_REPORT_DAYS = 365


def parse_stock_quantity(value, default=0):
    if value is None or value == '':
        value = default
    try:
        qty = float(value)
    except (TypeError, ValueError):
        raise ValidationError({'quantity': 'Must be a number'})
    if qty < 0 or qty > MAX_STOCK_QTY:
        raise ValidationError({'quantity': f'Must be between 0 and {MAX_STOCK_QTY}'})
    return qty


def parse_report_days(raw, default=30):
    if raw is None or raw == '':
        return default
    try:
        days = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({'days': 'Must be an integer'})
    if days < 1:
        raise ValidationError({'days': 'Must be at least 1'})
    return min(days, MAX_REPORT_DAYS)
