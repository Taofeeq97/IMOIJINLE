from rest_framework.permissions import BasePermission

from apps.accounts.policies import can


class RolePermission(BasePermission):
    """DRF permission that checks policies.can for required_action on view or subclass."""

    required_action: str | None = None

    def has_permission(self, request, view) -> bool:
        action = getattr(view, "required_action", None) or getattr(self, "required_action", None)
        if not action:
            return bool(request.user and request.user.is_authenticated)
        return can(request.user, action)

    def has_object_permission(self, request, view, obj) -> bool:
        action = getattr(view, "required_action", None) or getattr(self, "required_action", None)
        if not action:
            return bool(request.user and request.user.is_authenticated)
        return can(request.user, action, obj)
