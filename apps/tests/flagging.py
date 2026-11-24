"""Reference-range flagging shared by result entry and amendments."""


def apply_numeric_flag(result):
    param = result.parameter
    value = result.numeric_value
    result.flag = 'normal'
    critical = False

    if value is not None:
        if param.critical_high is not None and value > param.critical_high:
            result.flag = 'critical_high'
            critical = True
        elif param.critical_low is not None and value < param.critical_low:
            result.flag = 'critical_low'
            critical = True
        elif param.ref_range_high is not None and value > param.ref_range_high:
            result.flag = 'high'
        elif param.ref_range_low is not None and value < param.ref_range_low:
            result.flag = 'low'

    result.save(update_fields=['flag'])

    if critical and not result.order.is_critical:
        result.order.is_critical = True
        result.order.save(update_fields=['is_critical'])


def sync_order_review_status(order):
    """Move an in-progress order to review once every parameter has a value."""
    if order.status in ('cancelled', 'complete'):
        return
    expected = order.panel.parameters.count()
    entered = order.results.count()
    if expected and entered >= expected and order.status != 'review':
        order.status = 'review'
        order.save(update_fields=['status'])
