"""Read-only selectors for institution queries."""

from uuid import UUID

from django.db.models import Q, QuerySet

from .models import AcademicSession, Branch, Holiday, Institution, Shift, Term


def get_institution_by_id(institution_id: UUID | str) -> Institution | None:
    """Retrieve an active institution by ID."""
    return Institution.objects.filter(id=institution_id, is_active=True).first()


def get_current_academic_session(institution_id: UUID | str) -> AcademicSession | None:
    """Return the single current academic session for the given institution."""
    return AcademicSession.objects.filter(
        institution_id=institution_id,
        is_current=True,
    ).first()


def get_institution_branches(institution_id: UUID | str) -> QuerySet[Branch]:
    """Return all branches for an institution."""
    return Branch.objects.filter(institution_id=institution_id).order_by("code")


def get_branch_shifts(branch_id: UUID | str) -> QuerySet[Shift]:
    """Return all shifts for a branch."""
    return Shift.objects.filter(branch_id=branch_id).order_by("start_time")


def get_session_terms(session_id: UUID | str) -> QuerySet[Term]:
    """Return all terms in an academic session ordered by order."""
    return Term.objects.filter(session__id=session_id).order_by("order")


def get_institution_holidays(
    institution_id: UUID | str,
    branch_id: UUID | str | None = None,
) -> QuerySet[Holiday]:
    """Return holidays for an institution, optionally filtered by branch."""
    qs = Holiday.objects.filter(institution_id=institution_id)
    if branch_id:
        qs = qs.filter(Q(applies_to_all_branches=True) | Q(branches__id=branch_id)).distinct()
    return qs.order_by("-start_date")
