"""Notice publishing and visibility resolution service."""

import logging
from typing import TYPE_CHECKING, Any

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.communications.models import Notice, NoticeAudience

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.institutions.models import Institution

logger = logging.getLogger(__name__)


def create_notice(
    institution: "Institution",
    created_by: "User | None",
    title_en: str,
    content_en: str,
    title_bn: str = "",
    content_bn: str = "",
    category: str = "general",
    target_audience: str = NoticeAudience.ALL,
    target_class_level: Any = None,
    target_section: Any = None,
    is_pinned: bool = False,
    publish_date: Any = None,
    expiry_date: Any = None,
    attachment: Any = None,
) -> Notice:
    """Create a new notice."""
    return Notice.objects.create(
        institution=institution,
        created_by=created_by,
        title_en=title_en,
        title_bn=title_bn,
        content_en=content_en,
        content_bn=content_bn,
        category=category,
        target_audience=target_audience,
        target_class_level=target_class_level,
        target_section=target_section,
        is_pinned=is_pinned,
        publish_date=publish_date or timezone.now(),
        expiry_date=expiry_date,
        attachment=attachment,
    )


def get_visible_notices_for_user(
    institution: "Institution", user: "User | None"
) -> QuerySet[Notice]:
    """Resolve notice board items visible to a specific user based on roles and enrollment."""
    now = timezone.now()
    base_qs = Notice.objects.filter(
        institution=institution,
        is_published=True,
        publish_date__lte=now,
    ).filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=now))

    if not user or not user.is_authenticated:
        # Anonymous users can only see public ALL notices
        return base_qs.filter(target_audience=NoticeAudience.ALL)

    user_types = getattr(user, "user_types", []) or []
    if getattr(user, "is_superuser", False) or "institution_admin" in user_types:
        return base_qs

    # Audience filter based on roles
    audience_q = Q(target_audience=NoticeAudience.ALL)

    if any(r in user_types for r in ["teacher", "principal", "headmaster"]):
        audience_q |= Q(target_audience__in=[NoticeAudience.TEACHERS, NoticeAudience.STAFF])
    elif "staff" in user_types:
        audience_q |= Q(target_audience=NoticeAudience.STAFF)

    # Student matching
    student_profile = getattr(user, "student_profile", None)
    if student_profile:
        audience_q |= Q(target_audience=NoticeAudience.STUDENTS)
        # Class-specific notices
        enrollment = getattr(student_profile, "active_enrollment", None)
        if not enrollment and hasattr(student_profile, "enrollments"):
            enrollment = (
                student_profile.enrollments.filter(status="active").first()
                or student_profile.enrollments.first()
            )
        if enrollment:
            class_q = Q(target_audience=NoticeAudience.SPECIFIC_CLASS) & (
                Q(target_class_level=enrollment.class_level, target_section__isnull=True)
                | Q(target_section=enrollment.section)
            )
            audience_q |= class_q

    # Guardian matching
    guardian_profile = getattr(user, "guardian_profile", None)
    if guardian_profile:
        audience_q |= Q(target_audience=NoticeAudience.GUARDIANS)

    return base_qs.filter(audience_q).distinct()
