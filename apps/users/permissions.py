"""
Role-based access control for Lyncare.

Permissions are coarse-grained feature flags shared with the frontend via /api/users/me/.
"""

from rest_framework.permissions import BasePermission

# ── Permission constants ────────────────────────────────────────────────────────

PERMISSIONS = [
    'dashboard.view',
    'patients.view',
    'patients.create',
    'patients.delete',
    'visits.view',
    'visits.create',
    'clinical.vitals',
    'clinical.consultation',
    'clinical.diagnosis',
    'clinical.lab_order',
    'clinical.prescribe',
    'lab.view',
    'lab.results',
    'lab.panels_manage',
    'pharmacy.view',
    'pharmacy.otc',
    'pharmacy.dispense',
    'billing.view',
    'billing.payments',
    'billing.invoice',
    'inventory.view',
    'inventory.manage',
    'reports.print',
    'users.view',
    'users.manage',
    'roles.view',
]

# ── Role → permissions ────────────────────────────────────────────────────────

_RECEPTIONIST = {
    'dashboard.view',
    'patients.view',
    'patients.create',
    'visits.view',
    'visits.create',
    'reports.print',
}

_CLINICIAN = {
    'dashboard.view',
    'patients.view',
    'visits.view',
    'clinical.vitals',
    'clinical.consultation',
    'clinical.diagnosis',
    'clinical.lab_order',
    'clinical.prescribe',
    'lab.view',
    'reports.print',
}

_LAB_TECH = {
    'dashboard.view',
    'patients.view',
    'visits.view',
    'lab.view',
    'lab.results',
    'reports.print',
}

_PHARMACIST = {
    'dashboard.view',
    'patients.view',
    'visits.view',
    'pharmacy.view',
    'pharmacy.dispense',
    'pharmacy.otc',
    'reports.print',
}

_ACCOUNTANT = {
    'dashboard.view',
    'patients.view',
    'visits.view',
    'billing.view',
    'billing.payments',
    'billing.invoice',
    'pharmacy.otc',
    'reports.print',
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    'admin': set(PERMISSIONS),
    'receptionist': _RECEPTIONIST,
    'clinician': _CLINICIAN,
    'technician': _LAB_TECH,
    'pharmacist': _PHARMACIST,
    'accountant': _ACCOUNTANT,
    # Legacy aliases
    'manager': _ACCOUNTANT | {'inventory.view', 'inventory.manage', 'lab.panels_manage', 'visits.create', 'patients.create'},
    'scientist': _LAB_TECH | {'lab.panels_manage', 'inventory.view'},
}


def get_user_permissions(user) -> list[str]:
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return list(PERMISSIONS)
    role = getattr(user, 'role', 'receptionist')
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS['receptionist'])
    return sorted(perms)


def user_has_permission(user, permission: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return permission in get_user_permissions(user)


class HasPermission(BasePermission):
    """Instantiate with a permission string: HasPermission('patients.view')"""

    def __init__(self, permission: str):
        self.permission = permission

    def has_permission(self, request, view):
        return user_has_permission(request.user, self.permission)


class RBACMixin:
    """
    Map DRF actions to permissions. Set `rbac_map` on the viewset.

    Example:
        rbac_map = {
            'list': 'patients.view',
            'create': 'patients.create',
            'vitals': 'clinical.vitals',
        }
    """

    rbac_map: dict[str, str] = {}

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated

        perm = self.rbac_map.get(getattr(self, 'action', None))
        if perm:
            return [IsAuthenticated(), HasPermission(perm)]
        return [IsAuthenticated()]
