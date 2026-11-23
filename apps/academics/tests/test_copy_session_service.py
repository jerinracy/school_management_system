from datetime import date

import pytest

from apps.academics.models import ClassLevel, ClassSubject, Section, Subject
from apps.academics.services.copy_session import copy_academic_structure_from_previous_session
from apps.institutions.models import AcademicSession, Branch, Institution, Shift


@pytest.fixture
def copy_setup(db):
    inst = Institution.objects.create(name_en="Rollover High", eiin="993344")
    branch = Branch.objects.create(institution=inst, name="Main Campus")
    shift = Shift.objects.create(
        institution=inst, branch=branch, name="Day Shift", start_time="09:00", end_time="14:00"
    )

    s1 = AcademicSession.objects.create(
        institution=inst,
        name="Year 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    s2 = AcademicSession.objects.create(
        institution=inst,
        name="Year 2027",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
        is_current=False,
    )

    c7 = ClassLevel.objects.create(institution=inst, name="Class 7", code="C7", order=7)
    sec_a = Section.objects.create(
        institution=inst, class_level=c7, shift=shift, session=s1, branch=branch, name="A"
    )
    sec_b = Section.objects.create(
        institution=inst, class_level=c7, shift=shift, session=s1, branch=branch, name="B"
    )

    sub_math = Subject.objects.create(institution=inst, name_en="Mathematics", code="MATH101")
    ClassSubject.objects.create(
        institution=inst, class_level=c7, session=s1, subject=sub_math, full_marks=100
    )

    return {
        "institution": inst,
        "s1": s1,
        "s2": s2,
        "class7": c7,
        "sec_a": sec_a,
        "sec_b": sec_b,
        "sub_math": sub_math,
    }


def test_copy_session_dry_run_and_commit(copy_setup):
    """Test copy session service dry run returns preview counts, and commit creates them."""
    inst = copy_setup["institution"]
    s1 = copy_setup["s1"]
    s2 = copy_setup["s2"]

    # 1. Dry run simulation
    sim = copy_academic_structure_from_previous_session(
        institution_id=inst.id,
        source_session_id=s1.id,
        target_session_id=s2.id,
        copy_sections=True,
        copy_class_subjects=True,
        dry_run=True,
    )
    res_dict = sim.to_dict()
    assert res_dict["sections_count"] == 2
    assert res_dict["sections_created"] == 2
    assert res_dict["class_subjects_count"] == 1
    assert res_dict["class_subjects_created"] == 1
    assert len(res_dict["preview"]["sections"]) == 2
    assert len(res_dict["preview"]["class_subjects"]) == 1

    # Verify no records actually saved to DB
    assert Section.objects.filter(session=s2).count() == 0
    assert ClassSubject.objects.filter(session=s2).count() == 0

    # 2. Real commit
    commit = copy_academic_structure_from_previous_session(
        institution_id=inst.id,
        source_session_id=s1.id,
        target_session_id=s2.id,
        copy_sections=True,
        copy_class_subjects=True,
        dry_run=False,
    )
    c_dict = commit.to_dict()
    assert c_dict["sections_count"] == 2
    assert c_dict["sections_created"] == 2
    assert c_dict["class_subjects_count"] == 1
    assert c_dict["class_subjects_created"] == 1

    # Verify records actually created in DB for s2
    assert Section.objects.filter(session=s2).count() == 2
    assert ClassSubject.objects.filter(session=s2).count() == 1

    # 3. Idempotent re-run: duplicates are skipped
    rerun = copy_academic_structure_from_previous_session(
        institution_id=inst.id,
        source_session_id=s1.id,
        target_session_id=s2.id,
        copy_sections=True,
        copy_class_subjects=True,
        dry_run=False,
    )
    r_dict = rerun.to_dict()
    assert r_dict["sections_count"] == 0
    assert r_dict["skipped_sections_count"] == 2
    assert r_dict["class_subjects_count"] == 0
    assert r_dict["skipped_subjects_count"] == 1
