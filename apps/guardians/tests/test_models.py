"""Model tests for Guardian, Family, StudentGuardian, and AuthorizedPickup."""

import pytest
from django.db import IntegrityError, transaction

from apps.guardians.models import (
    AuthorizedPickup,
    Family,
    Guardian,
    GuardianRelation,
    StudentGuardian,
)
from apps.institutions.models import Institution
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Public School",
        name_bn="ঢাকা পাবলিক স্কুল",
        eiin="123456",
    )


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Chittagong High School",
        name_bn="চট্টগ্রাম উচ্চ বিদ্যালয়",
        eiin="654321",
    )


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="2026100001",
        name_en="Tanvir Ahmed",
        name_bn="তানভীর আহমেদ",
        gender="male",
        dob="2012-05-15",
        admission_date="2026-01-01",
    )


@pytest.mark.django_db
class TestGuardianModels:
    def test_create_family_and_guardian(self, institution):
        family = Family.objects.create(
            institution=institution,
            family_code="FAM-2026-00001",
            name="Ahmed Family",
            primary_contact_phone="+8801712345678",
        )
        guardian = Guardian.objects.create(
            institution=institution,
            family=family,
            name_en="Mustafizur Rahman",
            relation_default=GuardianRelation.FATHER,
            phone="+8801712345678",
            nid="19801234567890123",
        )
        assert guardian.family == family
        assert str(guardian) == "Mustafizur Rahman (+8801712345678)"
        assert str(family) == "FAM-2026-00001 - Ahmed Family"

    def test_unique_guardian_phone_per_institution(self, institution, other_institution):
        Guardian.objects.create(
            institution=institution,
            name_en="Guardian A",
            phone="+8801711111111",
        )
        # Duplicate in same institution raises IntegrityError
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                Guardian.objects.create(
                    institution=institution,
                    name_en="Guardian Duplicate",
                    phone="+8801711111111",
                )

        # Same phone in different institution is allowed
        other_g = Guardian.objects.create(
            institution=other_institution,
            name_en="Guardian In Other Inst",
            phone="+8801711111111",
        )
        assert other_g.id is not None

    def test_soft_deleted_guardian_allows_new_with_same_phone(self, institution):
        g1 = Guardian.objects.create(
            institution=institution,
            name_en="Old Guardian",
            phone="+8801722222222",
        )
        g1.delete()  # soft delete

        g2 = Guardian.objects.create(
            institution=institution,
            name_en="New Guardian",
            phone="+8801722222222",
        )
        assert g2.id is not None
        assert Guardian.objects.count() == 1
        assert Guardian.all_objects.count() == 2

    def test_student_guardian_unique_link(self, institution, student):
        guardian = Guardian.objects.create(
            institution=institution,
            name_en="Farhana Begum",
            relation_default=GuardianRelation.MOTHER,
            phone="+8801733333333",
        )
        link = StudentGuardian.objects.create(
            institution=institution,
            student=student,
            guardian=guardian,
            relation=GuardianRelation.MOTHER,
            is_primary=True,
        )
        assert str(link) == "Farhana Begum -> Tanvir Ahmed (Mother (মাতা))"

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                StudentGuardian.objects.create(
                    institution=institution,
                    student=student,
                    guardian=guardian,
                    relation=GuardianRelation.MOTHER,
                )

    def test_authorized_pickup_creation(self, institution, student):
        pickup = AuthorizedPickup.objects.create(
            institution=institution,
            student=student,
            name="Abdur Rashid",
            relation="Driver",
            phone="+8801744444444",
            nid="1985123456789",
        )
        assert pickup.is_active is True
        assert pickup.otp_verified is False
        assert "Driver" in str(pickup)
