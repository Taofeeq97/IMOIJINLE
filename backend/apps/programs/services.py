from __future__ import annotations

from django.db import transaction

from apps.audit.services import log_audit
from apps.courses.models import Subject, SubjectStatus, Subtopic, Topic
from apps.programs.models import (
    Class,
    ClassSubject,
    ClassTutor,
    Cohort,
    CohortStatus,
    PublishStatus,
    SubjectAttachMode,
)


def _audit(
    actor, action: str, obj, after: dict | None = None, before: dict | None = None, request=None
):
    log_audit(actor=actor, action=action, obj=obj, after=after, before=before, request=request)


def open_applications(*, cohort: Cohort, actor, request=None) -> Cohort:
    before = {"status": cohort.status}
    cohort.status = CohortStatus.APPLICATIONS_OPEN
    cohort.save(update_fields=["status", "updated_at"])
    _audit(
        actor,
        "cohort.open_applications",
        cohort,
        after={"status": cohort.status},
        before=before,
        request=request,
    )
    return cohort


def close_applications(*, cohort: Cohort, actor, request=None) -> Cohort:
    before = {"status": cohort.status}
    cohort.status = CohortStatus.APPLICATIONS_CLOSED
    cohort.save(update_fields=["status", "updated_at"])
    _audit(
        actor,
        "cohort.close_applications",
        cohort,
        after={"status": cohort.status},
        before=before,
        request=request,
    )
    return cohort


def publish_class(*, class_obj: Class, actor, request=None) -> Class:
    before = {"status": class_obj.status}
    class_obj.status = PublishStatus.PUBLISHED
    class_obj.save(update_fields=["status", "updated_at"])
    _audit(
        actor,
        "class.publish",
        class_obj,
        after={"status": class_obj.status},
        before=before,
        request=request,
    )
    return class_obj


def publish_subject(*, subject: Subject, actor, request=None) -> Subject:
    from apps.courses.services import publish_subject as _publish

    return _publish(subject=subject, actor=actor, request=request)


@transaction.atomic
def attach_subject(
    *,
    class_obj: Class,
    subject: Subject,
    mode: str = SubjectAttachMode.LINKED,
    actor=None,
    request=None,
) -> ClassSubject:
    order = class_obj.class_subjects.count()
    link, created = ClassSubject.objects.get_or_create(
        class_ref=class_obj,
        subject=subject,
        defaults={"order": order, "mode": mode},
    )
    if not created and link.mode != mode:
        link.mode = mode
        link.save(update_fields=["mode", "updated_at"])
    _audit(
        actor,
        "class.attach_subject",
        link,
        after={"class_id": str(class_obj.id), "subject_id": str(subject.id), "mode": mode},
        request=request,
    )
    return link


@transaction.atomic
def reorder_items(*, queryset, ordered_ids: list, id_attr: str = "id") -> None:
    id_to_order = {str(pk): idx for idx, pk in enumerate(ordered_ids)}
    for obj in queryset.filter(pk__in=ordered_ids):
        new_order = id_to_order.get(str(obj.pk))
        if new_order is not None and obj.order != new_order:
            obj.order = new_order
            obj.save(update_fields=["order", "updated_at"])


@transaction.atomic
def duplicate_class(*, class_obj: Class, actor=None, request=None) -> Class:
    clone = Class.objects.create(
        cohort=class_obj.cohort,
        name=f"{class_obj.name} (copy)",
        description=class_obj.description,
        status=PublishStatus.DRAFT,
        capacity=class_obj.capacity,
        starts_at=class_obj.starts_at,
        ends_at=class_obj.ends_at,
        order=class_obj.order + 1,
    )
    for link in class_obj.class_subjects.all():
        ClassSubject.objects.create(
            class_ref=clone,
            subject=link.subject,
            order=link.order,
            mode=SubjectAttachMode.LINKED,
        )
    _audit(actor, "class.duplicate", clone, after={"source_id": str(class_obj.id)}, request=request)
    return clone


@transaction.atomic
def duplicate_subject(*, subject: Subject, actor=None, request=None) -> Subject:
    clone = Subject.objects.create(
        title=f"{subject.title} (copy)",
        subtitle=subject.subtitle,
        description_json=subject.description_json,
        language=subject.language,
        level=subject.level,
        category=subject.category,
        subcategory=subject.subcategory,
        primary_topic_tags=subject.primary_topic_tags,
        intended_learners=subject.intended_learners,
        welcome_message=subject.welcome_message,
        completion_message=subject.completion_message,
        status=SubjectStatus.DRAFT,
        settings=subject.settings,
        version=1,
    )
    clone.instructors.set(subject.instructors.all())
    for topic in subject.topics.all():
        t_clone = Topic.objects.create(
            subject=clone,
            title=topic.title,
            objective_text=topic.objective_text,
            order=topic.order,
            is_published=False,
        )
        for sub in topic.subtopics.all():
            Subtopic.objects.create(
                topic=t_clone,
                title=sub.title,
                order=sub.order,
                kind=sub.kind,
                is_published=False,
                is_free_preview=sub.is_free_preview,
                estimated_time_s=sub.estimated_time_s,
                min_time_s=sub.min_time_s,
                description_json=sub.description_json,
                drip_rule=sub.drip_rule,
                unlock_rule=sub.unlock_rule,
            )
    _audit(actor, "subject.duplicate", clone, after={"source_id": str(subject.id)}, request=request)
    return clone


@transaction.atomic
def duplicate_cohort(*, cohort: Cohort, actor=None, request=None) -> Cohort:
    clone = Cohort.objects.create(
        program=cohort.program,
        name=f"{cohort.name} (copy)",
        description=cohort.description,
        timezone=cohort.timezone,
        capacity=cohort.capacity,
        status=CohortStatus.PLANNED,
        application_fee_kobo=cohort.application_fee_kobo,
        waitlist_enabled=cohort.waitlist_enabled,
        order=cohort.order,
    )
    for class_obj in cohort.classes.all():
        c = Class.objects.create(
            cohort=clone,
            name=class_obj.name,
            description=class_obj.description,
            status=PublishStatus.DRAFT,
            capacity=class_obj.capacity,
            order=class_obj.order,
        )
        for link in class_obj.class_subjects.all():
            ClassSubject.objects.create(
                class_ref=c,
                subject=link.subject,
                order=link.order,
                mode=SubjectAttachMode.LINKED,
            )
    _audit(actor, "cohort.duplicate", clone, after={"source_id": str(cohort.id)}, request=request)
    return clone


def ensure_class_tutor(
    *, class_obj: Class, user, role: str = "lead", actor=None, request=None
) -> ClassTutor:
    tutor, created = ClassTutor.objects.get_or_create(
        class_ref=class_obj, user=user, defaults={"role": role}
    )
    if created:
        _audit(
            actor,
            "class.assign_tutor",
            tutor,
            after={"class_id": str(class_obj.id), "user_id": str(user.id), "role": role},
            request=request,
        )
    return tutor
