from __future__ import annotations

from typing import Any

from apps.accounts.models import Role, RoleAssignment, User

# Permission strings exposed to the frontend via /auth/me
ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.SUPER_ADMIN: [
        "accounts.manage",
        "audit.view",
        "settings.manage",
        "impersonate",
        "programs.manage",
        "admissions.manage",
        "content.manage",
        "finance.view_all",
        "finance.manage",
        "certificates.manage",
        "teach",
        "grade",
        "learn",
        "apply",
    ],
    Role.PROGRAM_ADMIN: [
        "accounts.manage",
        "audit.view",
        "settings.manage",
        "impersonate",
        "programs.manage",
        "admissions.manage",
        "content.manage",
        "certificates.manage",
        "teach",
        "grade",
    ],
    Role.FINANCE_ADMIN: [
        "finance.view_all",
        "finance.manage",
        "audit.view",
        "settings.manage",
    ],
    Role.TUTOR: ["teach", "content.manage", "grade"],
    Role.TEACHING_ASSISTANT: ["teach", "grade"],
    Role.STUDENT: ["learn"],
    Role.OBSERVER: ["learn.view"],
    Role.APPLICANT: ["apply"],
}


def user_permissions(user: User) -> list[str]:
    if not user.is_authenticated:
        return []
    perms: set[str] = set()
    for assignment in user.role_assignments.all():
        perms.update(ROLE_PERMISSIONS.get(assignment.role, []))
    if user.is_superuser:
        perms.update(ROLE_PERMISSIONS[Role.SUPER_ADMIN])
    return sorted(perms)


def user_roles_payload(user: User) -> list[dict[str, Any]]:
    return [
        {
            "role": a.role,
            "scope_type": a.scope_type,
            "scope_id": str(a.scope_id) if a.scope_id else None,
        }
        for a in user.role_assignments.all()
    ]


def can(user: User | None, action: str, obj: Any = None) -> bool:
    """Deny-by-default central policy."""
    if user is None or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True

    roles = set(user.role_assignments.values_list("role", flat=True))
    if Role.SUPER_ADMIN in roles:
        return True

    allowed = set(user_permissions(user))
    if action in allowed:
        # Object-level scoping hooks (expanded in later milestones)
        if obj is not None and hasattr(obj, "user_id") and action.startswith("learn"):
            return obj.user_id == user.id
        return True
    return False


def has_role(user: User, *roles: str) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role_assignments.filter(role__in=roles).exists()


def assign_role(
    *,
    user: User,
    role: str,
    scope_type: str = "global",
    scope_id=None,
    actor: User | None = None,
    request=None,
) -> RoleAssignment:
    from apps.audit.services import log_audit

    assignment, created = RoleAssignment.objects.get_or_create(
        user=user,
        role=role,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    if created:
        log_audit(
            actor=actor,
            action="role.assign",
            obj=assignment,
            after={
                "user_id": str(user.id),
                "role": role,
                "scope_type": scope_type,
                "scope_id": str(scope_id) if scope_id else None,
            },
            request=request,
        )
    return assignment
