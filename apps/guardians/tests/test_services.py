"""Service tests for Guardian, Family, and Pickup services."""

import pytest

from apps.accounts.models import UserType
from apps.guardians.models import Family, GuardianRelation, StudentGuardian
from apps.guardians.services import (
    create_or_update_guardian,
    create_portal_user_for_guardian,
    generate_family_code,
    generate_pickup_verification_otp,
    link_siblings_to_family,
    link_student_guardian,
    merge_duplicate_guardians,
    register_pickup_person,
    suggest_siblings,
    unlink_student_guardian,
    verify_pickup_otp,
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
def students(db, institution) -> tuple[Student, Student]:
    s1 = Student.objects.create(
        institution=institution,
        student_id="2026100001",
        name_en="Tanvir Ahmed",
        gender="male",
        dob="2012-05-15",
        admission_date="2026-01-01",
        emergency_contact_phone="+8801711000000",
    )
    s2 = Student.objects.create(
        institution=institution,
        student_id="2026100002",
        name_en="Tahmina Ahmed",
        gender="female",
        dob="2014-08-20",
        admission_date="2026-01-01",
        emergency_contact_phone="+8801711000000",
    )
    return s1, s2


@pytest.mark.django_db
class TestGuardianServices:
    def test_create_or_update_guardian_normalizes_phone(self, institution):
        g = create_or_update_guardian(
            institution=institution,
            phone="01711223344",  # local format
            name_en="Kabir Hossain",
            nid="19801234567890123",
        )
        assert g.phone == "+8801711223344"
        assert g.nid == "19801234567890123"

        # Update with existing phone updates fields
        g_updated = create_or_update_guardian(
            institution=institution,
            phone="+8801711223344",
            name_en="Kabir Hossain Updated",
            occupation="Engineer",
        )
        assert g_updated.id == g.id
        assert g_updated.name_en == "Kabir Hossain Updated"
        assert g_updated.occupation == "Engineer"

    def test_create_portal_user_for_guardian(self, institution):
        guardian = create_or_update_guardian(
            institution=institution,
            phone="01799887766",
            name_en="Nusrat Jahan",
            email="nusrat@example.com",
        )
        user, temp_password = create_portal_user_for_guardian(guardian)

        assert user.user_type == UserType.GUARDIAN
        assert user.phone == "+8801799887766"
        assert user.check_password(temp_password)
        guardian.refresh_from_db()
        assert guardian.user == user

    def test_link_student_guardian_primary_enforcement(self, institution, students):
        s1, s2 = students
        g1 = create_or_update_guardian(
            institution=institution,
            phone="01711000001",
            name_en="Father 1",
        )
        g2 = create_or_update_guardian(
            institution=institution,
            phone="01711000002",
            name_en="Mother 1",
        )

        # Link g1 as primary
        link1 = link_student_guardian(
            institution=institution,
            student=s1,
            guardian=g1,
            relation=GuardianRelation.FATHER,
            is_primary=True,
        )
        assert link1.is_primary is True
        s1.refresh_from_db()
        assert s1.emergency_contact_phone == g1.phone
        assert s1.emergency_contact_name == g1.name_en

        # Link g2 as primary -> g1 should be demoted
        link2 = link_student_guardian(
            institution=institution,
            student=s1,
            guardian=g2,
            relation=GuardianRelation.MOTHER,
            is_primary=True,
        )
        assert link2.is_primary is True
        link1.refresh_from_db()
        assert link1.is_primary is False
        s1.refresh_from_db()
        assert s1.emergency_contact_phone == g2.phone
        assert s1.emergency_contact_name == g2.name_en

    def test_unlink_student_guardian_promotes_next(self, institution, students):
        s1, _ = students
        g1 = create_or_update_guardian(institution=institution, phone="01711000010", name_en="G1")
        g2 = create_or_update_guardian(institution=institution, phone="01711000020", name_en="G2")

        link_student_guardian(institution, s1, g1, is_primary=True)
        link_student_guardian(institution, s1, g2, is_primary=False)

        # Unlink primary g1 -> g2 becomes primary
        unlinked = unlink_student_guardian(institution, s1, g1)
        assert unlinked is True
        assert not StudentGuardian.objects.filter(student=s1, guardian=g1).exists()

        remaining = StudentGuardian.objects.get(student=s1, guardian=g2)
        assert remaining.is_primary is True
        s1.refresh_from_db()
        assert s1.emergency_contact_phone == g2.phone

    def test_merge_duplicate_guardians(self, institution, students):
        s1, s2 = students
        primary_g = create_or_update_guardian(
            institution=institution,
            phone="01711333333",
            name_en="Primary Guardian",
        )
        dup1 = create_or_update_guardian(
            institution=institution,
            phone="01711444444",
            name_en="Duplicate Guardian 1",
            nid="1982123456789",
        )
        dup2 = create_or_update_guardian(
            institution=institution,
            phone="01711555555",
            name_en="Duplicate Guardian 2",
        )

        link_student_guardian(institution, s1, primary_g, is_primary=True)
        link_student_guardian(institution, s2, dup1, is_primary=True)

        merged = merge_duplicate_guardians(
            institution=institution,
            primary_guardian=primary_g,
            duplicate_guardians=[dup1, dup2],
        )

        assert merged.id == primary_g.id
        assert merged.nid == "1982123456789"  # adopted from dup1
        # s2 link should now belong to primary_g
        assert StudentGuardian.objects.filter(student=s2, guardian=primary_g).exists()
        # dup1 and dup2 should be soft deleted
        assert dup1.is_deleted is True
        assert dup2.is_deleted is True

    def test_family_code_and_sibling_suggestions(self, institution, students):
        s1, s2 = students
        code = generate_family_code(institution)
        assert code.startswith("FAM-")

        family = Family.objects.create(
            institution=institution,
            family_code=code,
            name="Ahmed Household",
            primary_contact_phone="+8801711000000",
        )

        # Both students have emergency_contact_phone="+8801711000000"
        suggestions = suggest_siblings(institution, student=s1)
        assert len(suggestions) == 1
        assert suggestions[0]["student_id"] == str(s2.id)

        # Link to family
        g = create_or_update_guardian(
            institution=institution, phone="01711000000", name_en="Father"
        )
        link_student_guardian(institution, s1, g)
        link_student_guardian(institution, s2, g)

        link_siblings_to_family(institution, family, [str(s1.id), str(s2.id)])
        g.refresh_from_db()
        assert g.family == family

    def test_pickup_registration_and_otp(self, institution, students):
        s1, _ = students
        pickup = register_pickup_person(
            institution=institution,
            student=s1,
            name="Rafiqul Islam",
            relation="Uncle",
            phone="01788776655",
        )
        assert pickup.phone == "+8801788776655"
        assert pickup.otp_verified is False

        otp = generate_pickup_verification_otp(pickup)
        assert len(otp) == 6

        # Wrong OTP fails
        assert verify_pickup_otp(pickup, "000000") is False
        assert pickup.otp_verified is False

        # Correct OTP succeeds
        assert verify_pickup_otp(pickup, otp) is True
        pickup.refresh_from_db()
        assert pickup.otp_verified is True
        assert pickup.otp_verified_at is not None
