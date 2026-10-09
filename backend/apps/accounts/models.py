from __future__ import annotations

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone as dj_timezone

from apps.common.models import BaseModel, new_uuid


class UserManager(BaseUserManager["User"]):
    def create_user(self, email: str, password: str | None = None, **extra_fields) -> User:
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=new_uuid, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    locale = models.CharField(max_length=16, default="en")
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    totp_secret = models.CharField(max_length=64, blank=True, null=True)
    date_joined = models.DateTimeField(default=dj_timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    PROGRAM_ADMIN = "program_admin", "Program Admin"
    FINANCE_ADMIN = "finance_admin", "Finance Admin"
    TUTOR = "tutor", "Tutor"
    TEACHING_ASSISTANT = "teaching_assistant", "Teaching Assistant"
    STUDENT = "student", "Student"
    OBSERVER = "observer", "Observer"
    APPLICANT = "applicant", "Applicant"


class ScopeType(models.TextChoices):
    GLOBAL = "global", "Global"
    PROGRAM = "program", "Program"
    COHORT = "cohort", "Cohort"
    CLASS = "class", "Class"


class RoleAssignment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.CharField(max_length=32, choices=Role.choices)
    scope_type = models.CharField(max_length=16, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    scope_id = models.UUIDField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "scope_type", "scope_id"],
                name="uniq_role_assignment",
            )
        ]
        ordering = ["role"]

    def __str__(self) -> str:
        return f"{self.user.email}:{self.role}:{self.scope_type}"


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True)
    country = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=64, blank=True)
    gender = models.CharField(max_length=32, blank=True)
    dob = models.DateField(null=True, blank=True)
    occupation = models.CharField(max_length=128, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    consent_flags = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.email}>"


class Invitation(BaseModel):
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=32, choices=Role.choices)
    scope_type = models.CharField(max_length=16, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    scope_id = models.UUIDField(null=True, blank=True)
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="invitations_sent"
    )


class MagicLinkToken(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="magic_links")
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
