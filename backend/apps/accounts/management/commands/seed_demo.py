from django.core.management.base import BaseCommand

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.courses.models import (
    ContentType,
    Subject,
    SubjectLevel,
    SubjectStatus,
    Subtopic,
    SubtopicContent,
    SubtopicKind,
    Topic,
)
from apps.orgsettings.models import (
    ApplicationFeeSettings,
    BrandSettings,
    FeatureFlag,
    PaymentGatewaySettings,
    SiteSettings,
)
from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.programs.models import (
    Class,
    ClassSubject,
    Cohort,
    CohortStatus,
    PublishStatus,
    SubjectAttachMode,
)
from apps.programs.services import ensure_class_tutor

DEMO_PASSWORD = "DemoPass123!"

SEED_USERS = [
    ("superadmin@imoijinle.local", "Super", "Admin", Role.SUPER_ADMIN, True, True),
    ("programadmin@imoijinle.local", "Program", "Admin", Role.PROGRAM_ADMIN, True, False),
    ("financeadmin@imoijinle.local", "Finance", "Admin", Role.FINANCE_ADMIN, True, False),
    ("tutor@imoijinle.local", "Tutor", "Demo", Role.TUTOR, False, False),
    ("ta@imoijinle.local", "Teaching", "Assistant", Role.TEACHING_ASSISTANT, False, False),
    ("student@imoijinle.local", "Student", "Demo", Role.STUDENT, False, False),
    ("observer@imoijinle.local", "Observer", "Demo", Role.OBSERVER, False, False),
    ("applicant@imoijinle.local", "Applicant", "Demo", Role.APPLICANT, False, False),
]


class Command(BaseCommand):
    help = "Seed demo users, hierarchy, and payment settings."

    def handle(self, *args, **options):
        brand = BrandSettings.get_solo()
        brand.org_name = "Imo Ijinle Academy"
        brand.save()
        SiteSettings.get_solo()
        FeatureFlag.objects.get_or_create(
            key="course_review_required",
            defaults={"enabled": False, "description": "Require in_review before publish"},
        )
        PaymentGatewaySettings.get_solo()
        fees = ApplicationFeeSettings.get_solo()
        fees.default_amount_kobo = 500000
        fees.is_free = False
        fees.fee_required_before_admit = True
        fees.save()

        from apps.orgsettings.payment_services import encrypt_secret

        gw = PaymentGatewaySettings.get_solo()
        # Prefer real keys from environment; do not invent mock secrets
        import os

        if os.environ.get("PAYSTACK_PUBLIC_KEY") and not gw.public_key:
            gw.public_key = os.environ["PAYSTACK_PUBLIC_KEY"]
        if os.environ.get("PAYSTACK_SECRET_KEY") and not gw.secret_key_encrypted:
            gw.secret_key_encrypted = encrypt_secret(os.environ["PAYSTACK_SECRET_KEY"])
        gw.mode = "test"
        gw.save()

        users: dict[str, User] = {}
        for email, first, last, role, is_staff, is_super in SEED_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "is_staff": is_staff,
                    "is_superuser": is_super,
                    "is_active": True,
                },
            )
            user.first_name = first
            user.last_name = last
            user.is_staff = is_staff
            user.is_superuser = is_super
            user.set_password(DEMO_PASSWORD)
            user.save()
            assign_role(user=user, role=role, actor=user)
            users[email] = user
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} {email} ({role})"))

        # Cohort is the root container (= academic session). No Program entity in product model.
        cohort_open, _ = Cohort.objects.get_or_create(
            slug="jan-2027-intake",
            defaults={
                "name": "2026/2027 Academic Session",
                "status": CohortStatus.APPLICATIONS_OPEN,
                "capacity": 80,
                "application_fee_kobo": 500000,
            },
        )
        cohort_open.program = None
        cohort_open.name = "2026/2027 Academic Session"
        cohort_open.status = CohortStatus.APPLICATIONS_OPEN
        cohort_open.capacity = 80
        cohort_open.application_fee_kobo = 500000
        cohort_open.save()
        cohort_running, _ = Cohort.objects.get_or_create(
            slug="sep-2026-running",
            defaults={
                "name": "2025/2026 Academic Session",
                "status": CohortStatus.RUNNING,
                "capacity": 60,
            },
        )
        cohort_running.program = None
        cohort_running.name = "2025/2026 Academic Session"
        cohort_running.status = CohortStatus.RUNNING
        cohort_running.save()

        foundation, _ = Class.objects.get_or_create(
            cohort=cohort_open,
            slug="foundation-class",
            defaults={
                "name": "Foundation Class",
                "description": "Entry class for new applicants.",
                "status": PublishStatus.PUBLISHED,
                "order": 0,
            },
        )
        advanced, _ = Class.objects.get_or_create(
            cohort=cohort_open,
            slug="advanced-class",
            defaults={
                "name": "Advanced Class",
                "description": "Draft advanced track.",
                "status": PublishStatus.DRAFT,
                "order": 1,
            },
        )
        Class.objects.get_or_create(
            cohort=cohort_running,
            slug="foundation-class",
            defaults={
                "name": "Foundation Class",
                "status": PublishStatus.PUBLISHED,
                "order": 0,
            },
        )

        subject_intro, _ = Subject.objects.get_or_create(
            slug="introduction-to-spirit-science",
            defaults={
                "title": "Introduction to Spirit Science",
                "subtitle": "Orientation and foundations",
                "level": SubjectLevel.BEGINNER,
                "status": SubjectStatus.PUBLISHED,
                "category": "Foundations",
                "description_json": {"html": "<p>Orientation and foundations for Spirit Science.</p>"},
                "welcome_message": "Welcome to Introduction to Spirit Science.",
                "completion_message": "You completed the foundations subject.",
                "pricing": {"mode": "class_fee", "amount_kobo": 0, "currency": "NGN"},
                "intended_learners": {
                    "learn": ["Core concepts", "Study rhythm", "Community norms", "Practice basics"],
                    "requirements": ["Open mind"],
                    "audience": ["New students"],
                },
            },
        )
        subject_intro.description_json = subject_intro.description_json or {
            "html": "<p>Orientation and foundations for Spirit Science.</p>"
        }
        subject_intro.welcome_message = subject_intro.welcome_message or "Welcome to Introduction to Spirit Science."
        subject_intro.completion_message = (
            subject_intro.completion_message or "You completed the foundations subject."
        )
        subject_intro.pricing = subject_intro.pricing or {
            "mode": "class_fee",
            "amount_kobo": 0,
            "currency": "NGN",
        }
        subject_intro.save()
        subject_practice, _ = Subject.objects.get_or_create(
            slug="daily-practice",
            defaults={
                "title": "Daily Practice",
                "subtitle": "Habits and reflection",
                "level": SubjectLevel.INTERMEDIATE,
                "status": SubjectStatus.DRAFT,
                "category": "Practice",
            },
        )
        subject_intro.instructors.add(users["tutor@imoijinle.local"])

        for subject in (subject_intro, subject_practice):
            if subject.topics.exists():
                continue
            for ti, topic_title in enumerate(["Getting started", "Going deeper"]):
                topic = Topic.objects.create(
                    subject=subject,
                    title=topic_title,
                    objective_text=f"Complete {topic_title.lower()}.",
                    order=ti,
                    is_published=subject.status == SubjectStatus.PUBLISHED,
                )
                for si, (sub_title, kind) in enumerate(
                    [
                        ("Welcome", SubtopicKind.SUBTOPIC),
                        ("Check-in quiz", SubtopicKind.QUIZ),
                    ]
                ):
                    Subtopic.objects.create(
                        topic=topic,
                        title=sub_title,
                        order=si,
                        kind=kind,
                        is_published=subject.status == SubjectStatus.PUBLISHED,
                        estimated_time_s=600,
                        min_time_s=120,
                    )

        # Sample lesson content for authoring / learning demo
        welcome = Subtopic.objects.filter(topic__subject=subject_intro, title="Welcome").first()
        if welcome:
            welcome.is_free_preview = True
            welcome.min_time_s = 30
            welcome.save(update_fields=["is_free_preview", "min_time_s", "updated_at"])
            if not SubtopicContent.objects.filter(subtopic=welcome).exists():
                SubtopicContent.objects.create(
                    subtopic=welcome,
                    content_type=ContentType.ARTICLE,
                    title="Welcome article",
                    body_json={"html": "<p>Welcome to the academy. Read this orientation carefully.</p>"},
                    processing_status="ready",
                    duration_s=300,
                )

        ClassSubject.objects.get_or_create(
            class_ref=foundation,
            subject=subject_intro,
            defaults={"order": 0, "mode": SubjectAttachMode.LINKED},
        )
        ClassSubject.objects.get_or_create(
            class_ref=foundation,
            subject=subject_practice,
            defaults={"order": 1, "mode": SubjectAttachMode.CLONED},
        )
        ClassSubject.objects.get_or_create(
            class_ref=advanced,
            subject=subject_practice,
            defaults={"order": 0, "mode": SubjectAttachMode.LINKED},
        )

        ensure_class_tutor(
            class_obj=foundation,
            user=users["tutor@imoijinle.local"],
            role="lead",
            actor=users["superadmin@imoijinle.local"],
        )

        enrollment, _ = Enrollment.objects.get_or_create(
            user=users["student@imoijinle.local"],
            class_ref=foundation,
            defaults={
                "cohort": foundation.cohort,
                "status": EnrollmentStatus.ACTIVE,
            },
        )

        from apps.payments.models import (
            FeeBilling,
            FeeItem,
            FeeItemKind,
            FeeMode,
            FeeRule,
            FeeScopeType,
            Invoice,
            InvoiceKind,
            InvoiceLine,
            InvoiceSource,
            InvoiceStatus,
            PaymentNotificationConfig,
        )

        class_fee, _ = FeeItem.objects.get_or_create(
            code="class-foundation-fee",
            defaults={
                "name": "Foundation Class Fee",
                "kind": FeeItemKind.TUITION,
                "amount_minor": 15000000,  # ₦150,000
                "currency": "NGN",
                "description": "Tuition for Foundation Class",
                "active": True,
            },
        )
        FeeRule.objects.get_or_create(
            fee_item=class_fee,
            scope_type=FeeScopeType.CLASS,
            scope_id=foundation.id,
            defaults={
                "mode": FeeMode.MANDATORY,
                "billing": FeeBilling.ONE_OFF,
                "gate_rule": {"block": f"class:{foundation.id}", "grace_days": 0},
                "priority": 10,
                "active": True,
            },
        )
        PaymentNotificationConfig.objects.get_or_create(
            scope_type="global",
            scope_id=None,
            event="payment_succeeded",
            defaults={
                "enabled": True,
                "channels": ["email", "in_app"],
                "recipients": ["student", "finance_team"],
                "offsets": [],
                "quiet_hours": {"start": "21:00", "end": "07:00", "tz": "Africa/Lagos"},
            },
        )

        student = users["student@imoijinle.local"]
        if not Invoice.objects.filter(user=student, fee_item=class_fee, status=InvoiceStatus.OPEN).exists():
            inv = Invoice.objects.create(
                user=student,
                number=f"IMO-SEED-{foundation.slug}",
                kind=InvoiceKind.CLASS,
                status=InvoiceStatus.OPEN,
                currency="NGN",
                amount_minor=class_fee.amount_minor,
                description=class_fee.name,
                source=InvoiceSource.RULE,
                enrollment=enrollment,
                fee_item=class_fee,
                gate_rule={"block": f"class:{foundation.id}", "grace_days": 0},
                metadata={"class_id": str(foundation.id), "seed": True},
            )
            InvoiceLine.objects.create(
                invoice=inv,
                fee_item=class_fee,
                description=class_fee.name,
                amount_minor=class_fee.amount_minor,
                installment_no=1,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded program, cohorts, classes, subjects, topics, payment settings, "
                "class fee rule, sample unpaid invoice, student enrollment"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Demo password for all: {DEMO_PASSWORD}"))
