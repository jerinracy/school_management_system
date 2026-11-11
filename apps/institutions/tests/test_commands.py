"""Test for seed_demo_institution management command."""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.institutions.models import AcademicSession, Branch, Holiday, Institution, Shift, Term


@pytest.mark.django_db
class TestSeedDemoInstitutionCommand:
    def test_seed_demo_institution_execution(self) -> None:
        out = StringIO()
        call_command("seed_demo_institution", stdout=out)
        output = out.getvalue()

        assert "Created institution: Dhaka Model High School & College" in output
        assert "Created branch: Main Campus (Dhanmondi)" in output
        assert "Created Morning and Day shifts" in output
        assert "Created active academic session: 2026" in output
        assert "Created 3 academic terms for 2026" in output
        assert "Seeded BD public holidays for 2026" in output

        # Verify database objects
        institution = Institution.objects.get(eiin="134567")
        assert institution.name_en == "Dhaka Model High School & College"
        assert Branch.objects.filter(institution=institution).count() == 1
        assert Shift.objects.filter(institution=institution).count() == 2
        assert AcademicSession.objects.filter(institution=institution, is_current=True).count() == 1
        assert Term.objects.filter(institution=institution).count() == 3
        assert Holiday.objects.filter(institution=institution).count() == 7

        # Re-running is idempotent and doesn't fail
        out_second = StringIO()
        call_command("seed_demo_institution", stdout=out_second)
        assert "Institution already exists" in out_second.getvalue()
