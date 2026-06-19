"""Visit workflow helpers — enforces stage order across apps."""

from __future__ import annotations

from apps.tests.models import TestOrder

# Allowed visit statuses in pipeline order (excluding cancelled)
PIPELINE = [
    'registered',
    'triage',
    'consultation',
    'lab',
    'results_ready',
    'prescription',
    'pharmacy',
    'completed',
]

# Which statuses each workflow action accepts
STAGE_REQUIREMENTS = {
    'vitals': ('registered', 'triage'),
    'consultation': ('registered', 'triage', 'consultation'),
    'lab_orders': ('consultation',),
    'skip_lab': ('consultation',),
    'diagnosis': ('results_ready',),
    'prescription': ('prescription',),
    'dispense': ('prescription', 'pharmacy'),
    'bill': ('pharmacy', 'prescription', 'completed'),
}


def stage_index(status: str) -> int:
    try:
        return PIPELINE.index(status)
    except ValueError:
        return -1


def assert_stage(visit, action: str) -> str | None:
    """Return error message if visit is not in a valid stage for action."""
    allowed = STAGE_REQUIREMENTS.get(action)
    if not allowed:
        return None
    if visit.status not in allowed:
        labels = ', '.join(allowed)
        return f'Visit must be at stage: {labels} (current: {visit.status})'
    return None


def visit_lab_orders(visit):
    return TestOrder.objects.filter(visit=visit).exclude(status='cancelled')


def sync_visit_after_lab(visit) -> None:
    """Advance visit to results_ready when all linked lab orders are complete."""
    if visit.status != 'lab':
        return
    orders = visit_lab_orders(visit)
    if not orders.exists():
        return
    pending = orders.exclude(status='complete')
    if not pending.exists():
        visit.advance('results_ready')


def sync_visit_after_dispense(visit) -> None:
    """Move visit to pharmacy stage after medication is dispensed."""
    if visit.status in ('prescription', 'pharmacy'):
        visit.advance('pharmacy')


def sync_visit_after_payment(visit) -> None:
    """Mark visit completed when linked invoice is fully paid."""
    if visit.status in ('pharmacy', 'prescription', 'completed'):
        visit.advance('completed')
