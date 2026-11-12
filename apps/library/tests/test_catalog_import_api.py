"""Tests for library Excel catalog import, barcode/RFID scan API, reports, RBAC, and tenant isolation."""

import io
from datetime import date, timedelta

import openpyxl
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.institutions.models import Branch, Institution
from apps.library.models import Book, BookCopy, LibraryMember, LibraryMemberType
from apps.students.models import Gender, Student


def _grant_library_perms(user: User, codenames: list[str]) -> None:
    assert user.institution is not None
    ct = ContentType.objects.get_for_model(Book)
    role = Role.objects.create(
        institution=user.institution,
        name=f"LibRole-{user.username}",
        code=f"lib_role_{user.username}",
    )
    for code in codenames:
        short = code.split(".")[-1]
        perm, _ = Permission.objects.get_or_create(
            codename=short, content_type=ct, defaults={"name": code}
        )
        role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)


def _build_catalog_xlsx(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.mark.django_db
class TestLibraryCatalogImportAndAPI:
    def setup_method(self) -> None:
        self.inst_a = Institution.objects.create(name_en="School A", name_bn="স্কুল ক")
        self.inst_b = Institution.objects.create(name_en="School B", name_bn="স্কুল খ")
        self.branch_a = Branch.objects.create(
            institution=self.inst_a, name="Main", code="MA", is_main=True
        )
        self.librarian = User.objects.create_user(
            username="librarian_a",
            password="pass",
            institution=self.inst_a,
            user_type=UserType.STAFF,
        )
        _grant_library_perms(self.librarian, ["library.view", "library.manage", "library.issue"])
        self.student_user = User.objects.create_user(
            username="STU-A1",
            password="pass",
            institution=self.inst_a,
            user_type=UserType.STUDENT,
        )
        self.student = Student.objects.create(
            institution=self.inst_a,
            student_id="STU-A1",
            name_en="Tasnim Akter",
            name_bn="তাসনিম আক্তার",
            dob=date(2012, 3, 1),
            gender=Gender.FEMALE,
            admission_date=date(2026, 1, 10),
            emergency_contact_name="Kamal Uddin",
            emergency_contact_phone="+8801711000099",
        )
        self.member_a = LibraryMember.objects.create(
            institution=self.inst_a,
            member_type=LibraryMemberType.STUDENT,
            student=self.student,
            branch=self.branch_a,
            card_number="CARD-A1",
            rfid_card_uid="RFID-USER-A1",
        )
        self.other_admin = User.objects.create_user(
            username="librarian_b",
            password="pass",
            institution=self.inst_b,
            user_type=UserType.STAFF,
        )
        _grant_library_perms(self.other_admin, ["library.view", "library.manage", "library.issue"])

    def test_excel_import_scan_issue_return_popular_overdue_and_history(self) -> None:
        client = APIClient()
        client.force_authenticate(user=self.librarian)

        xlsx_bytes = _build_catalog_xlsx(
            [
                [
                    "isbn",
                    "title",
                    "authors",
                    "category",
                    "accession_no",
                    "barcode",
                    "rfid_tag",
                    "price",
                ],
                [
                    "978-984-1",
                    "Gitanjali",
                    "Rabindranath Tagore",
                    "Literature",
                    "ACC-100",
                    "BC-100",
                    "RFID-100",
                    250,
                ],
                [
                    "978-984-2",
                    "Pather Panchali",
                    "Bibhutibhushan",
                    "Fiction",
                    "ACC-101",
                    "BC-101",
                    "RFID-101",
                    300,
                ],
            ]
        )
        upload = SimpleUploadedFile(
            "catalog.xlsx",
            xlsx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        import_resp = client.post(
            reverse("v1_library:book-import-xlsx"),
            {"file": upload, "branch": str(self.branch_a.id)},
            format="multipart",
        )
        assert import_resp.status_code == status.HTTP_200_OK
        assert import_resp.data["created_books"] == 2
        assert import_resp.data["created_copies"] == 2

        # Lookup copy by barcode
        lookup_resp = client.get(reverse("v1_library:copy-lookup"), {"barcode": "BC-100"})
        assert lookup_resp.status_code == status.HTTP_200_OK
        assert lookup_resp.data["accession_no"] == "ACC-100"

        # Issue via RFID card UID & barcode
        past_due = timezone.localdate() - timedelta(days=2)
        issue_resp = client.post(
            reverse("v1_library:issue-issue"),
            {
                "rfid_card_uid": "RFID-USER-A1",
                "barcode": "BC-100",
                "due_date": timezone.localdate().isoformat(),
            },
            format="json",
        )
        assert issue_resp.status_code == status.HTTP_201_CREATED
        issue_id = issue_resp.data["id"]

        # Force due_date to past to verify /overdue/ endpoint
        from apps.library.models import BookIssue

        BookIssue.objects.filter(id=issue_id).update(due_date=past_due)
        overdue_resp = client.get(reverse("v1_library:issue-overdue"))
        assert overdue_resp.status_code == status.HTTP_200_OK
        assert overdue_resp.data["count"] == 1

        # Popular books endpoint
        popular_resp = client.get(reverse("v1_library:book-popular"))
        assert popular_resp.status_code == status.HTTP_200_OK
        assert len(popular_resp.data) == 1
        assert popular_resp.data[0]["title"] == "Gitanjali"

        # Return via RFID tag
        return_resp = client.post(
            reverse("v1_library:issue-return-copy"),
            {"rfid_tag": "RFID-100"},
            format="json",
        )
        assert return_resp.status_code == status.HTTP_200_OK
        assert return_resp.data["status"] == "returned"

        # Member history endpoint shows past issue and overdue fine
        history_resp = client.get(
            reverse("v1_library:member-history", kwargs={"pk": str(self.member_a.id)})
        )
        assert history_resp.status_code == status.HTTP_200_OK
        assert len(history_resp.data["past_issues"]) == 1
        assert len(history_resp.data["fines"]) == 1

    def test_rbac_and_tenant_isolation(self) -> None:
        book_a = Book.objects.create(
            institution=self.inst_a, title="Bangla Grammar", authors="Dr. Shahidullah"
        )
        BookCopy.objects.create(
            institution=self.inst_a, book=book_a, accession_no="ACC-A1", barcode="BC-A1"
        )

        # Student can read catalog, cannot create books or issue
        student_client = APIClient()
        student_client.force_authenticate(user=self.student_user)
        assert student_client.get(reverse("v1_library:book-list")).status_code == status.HTTP_200_OK
        assert (
            student_client.post(
                reverse("v1_library:book-list"),
                {"title": "Hack", "authors": "X"},
                format="json",
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            student_client.post(
                reverse("v1_library:issue-issue"),
                {"card_number": "CARD-A1", "barcode": "BC-A1"},
                format="json",
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # Other tenant librarian cannot see School A's catalog or issue School A's copy
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_admin)
        list_resp = other_client.get(reverse("v1_library:book-list"))
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.data["count"] == 0
        assert (
            other_client.post(
                reverse("v1_library:issue-issue"),
                {"card_number": "CARD-A1", "barcode": "BC-A1"},
                format="json",
            ).status_code
            == status.HTTP_400_BAD_REQUEST
        )
