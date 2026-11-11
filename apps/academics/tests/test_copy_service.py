"""Unit tests for copying academic structure between sessions."""

from datetime import date, time

import pytest

from apps.academics.models import (
    ClassLevel,
    ClassSubject,
    Section,
    Subject,
)
from apps.academics.services.copy_session import copy_academic_structure_from_previous_session
from apps.institutions.models import AcademicSession, Branch, Institution, Shift


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(name_bn="আইডিয়াল স্কুল", name_en="Ideal School", eiin="112233")


@pytest.fixture
def branch(institution: Institution) -> Branch:
    return Branch.objects.create(institution=institution, name="Main Campus", code="MAIN")


@pytest.fixture
def source_session(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        is_current=False,
    )


@pytest.fixture
def target_session(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def shift(institution: Institution, branch: Branch) -> Shift:
    return Shift.objects.create(
        institution=institution,
        branch=branch,
        name="morning",
        start_time=time(7, 30),
        end_time=time(12, 0),
    )


@pytest.mark.django_db
class TestCopyAcademicStructure:
    def test_dry_run_previews_without_persisting(
        self,
        institution: Institution,
        source_session: AcademicSession,
        target_session: AcademicSession,
        shift: Shift,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 6", code="c06", order=6
        )
        Section.objects.create(
            institution=institution,
            class_level=cls,
            shift=shift,
            session=source_session,
            name="Padma",
        )
        sub = Subject.objects.create(
            institution=institution, code="101", name_en="Bangla", name_bn="বাংলা"
        )
        ClassSubject.objects.create(
            institution=institution, class_level=cls, session=source_session, subject=sub
        )

        # Run dry run
        result = copy_academic_structure_from_previous_session(
            institution_id=institution.id,
            source_session_id=source_session.id,
            target_session_id=target_session.id,
            copy_sections=True,
            copy_class_subjects=True,
            dry_run=True,
        )
        assert result.dry_run is True
        assert result.sections_count == 1
        assert result.class_subjects_count == 1
        assert len(result.preview["sections"]) == 1

        # Confirm target session remains empty
        assert Section.objects.filter(session=target_session).count() == 0
        assert ClassSubject.objects.filter(session=target_session).count() == 0

    def test_actual_copy_persists_records(
        self,
        institution: Institution,
        source_session: AcademicSession,
        target_session: AcademicSession,
        shift: Shift,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 7", code="c07", order=7
        )
        Section.objects.create(
            institution=institution,
            class_level=cls,
            shift=shift,
            session=source_session,
            name="Meghna",
        )
        sub = Subject.objects.create(
            institution=institution, code="107", name_en="English", name_bn="ইংরেজি"
        )
        ClassSubject.objects.create(
            institution=institution, class_level=cls, session=source_session, subject=sub
        )

        result = copy_academic_structure_from_previous_session(
            institution_id=institution.id,
            source_session_id=source_session.id,
            target_session_id=target_session.id,
            copy_sections=True,
            copy_class_subjects=True,
            dry_run=False,
        )
        assert result.dry_run is False
        assert result.sections_count == 1
        assert result.class_subjects_count == 1

        # Check records created in target session
        assert Section.objects.filter(session=target_session, name="Meghna").count() == 1
        assert ClassSubject.objects.filter(session=target_session, subject=sub).count() == 1

    def test_skips_already_existing_target_sections(
        self,
        institution: Institution,
        source_session: AcademicSession,
        target_session: AcademicSession,
        shift: Shift,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 8", code="c08", order=8
        )
        Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=source_session, name="A"
        )
        # Pre-create in target
        Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=target_session, name="A"
        )

        result = copy_academic_structure_from_previous_session(
            institution_id=institution.id,
            source_session_id=source_session.id,
            target_session_id=target_session.id,
            copy_sections=True,
            copy_class_subjects=False,
            dry_run=False,
        )
        assert result.sections_count == 0
        assert result.skipped_sections_count == 1
        assert Section.objects.filter(session=target_session).count() == 1
