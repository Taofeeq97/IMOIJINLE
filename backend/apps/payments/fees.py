"""Fee resolution, custom charges, gating, refunds, and finance helpers.

Re-exports and thin wrappers around apps.payments.services for admissions hooks
and any callers that historically imported from this module.
"""

from __future__ import annotations

from apps.payments.services import (
    apply_fee_rules_on_admit,
    can_access_class,
    can_access_subject,
    create_custom_charge,
    explain_access,
    finance_aging,
    finance_attempts_vs_paid,
    finance_outstanding,
    finance_overview,
    generate_installment_lines,
    preview_custom_charge,
    request_refund,
    resolve_fees_for_enrollment,
)


def resolve_fee_rules_for_enrollment(enrollment):
    return resolve_fees_for_enrollment(enrollment)


def generate_invoices_for_enrollment(*, enrollment, actor=None, request=None):
    return apply_fee_rules_on_admit(enrollment=enrollment, actor=actor, request=request)


__all__ = [
    "apply_fee_rules_on_admit",
    "can_access_class",
    "can_access_subject",
    "create_custom_charge",
    "explain_access",
    "finance_aging",
    "finance_attempts_vs_paid",
    "finance_outstanding",
    "finance_overview",
    "generate_installment_lines",
    "generate_invoices_for_enrollment",
    "preview_custom_charge",
    "request_refund",
    "resolve_fee_rules_for_enrollment",
    "resolve_fees_for_enrollment",
]
