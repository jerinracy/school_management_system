"""Tests for Notice Board receipts, Unified Calendar, Events, Clubs, Certificates & Gallery."""

from datetime import date, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.communications.models import Notice, NoticeAudience, NoticeCategory
from apps.events.models import (
    Achievement,
    Album,
    Certificate,
    Club,
    ClubCategory,
    ClubMembership,
    Competition,
    CompetitionLevel,
    CompetitionPosition,
    CompetitionResult,
    Event,
    EventCategory,
    GalleryMedia,
    GalleryMediaType,
    RSVPStatus,
)
from apps.institutions.models import Holiday, HolidayType, Institution
from apps.students.models import Student


def _grant_permission(user: User, module: str, codename: str) -> None:
    ct = ContentType.objects.get_for_model(Event)
    perm, _ = Permission.objects.get_or_create(
        codename=codename,
        content_type=ct,
        defaults={"name": f"{module}.{codename}"},
    )
    role, _ = Role.objects.get_or_create(
        institution=user.institution,
        code=f"role_{module}_{codename}",
        defaults={"name": f"Role-{module}-{codename}"},
    )
    role.permissions.add(perm)
    UserRole.objects.get_or_create(user=user, role=role)


@pytest.fixture
def events_env(db):
    inst = Institution.objects.create(
        name_en="Dhaka Model School",
        name_bn="ঢাকা মডেল স্কুল",
        eiin="108801",
    )
    other_inst = Institution.objects.create(
        name_en="Other School",
        name_bn="অন্য স্কুল",
        eiin="108802",
    )
    admin = User.objects.create_user(
        username="ev_admin",
        password="Password123!",
        phone="+8801711000010",
        institution=inst,
        user_type=UserType.ADMIN,
    )
    _grant_permission(admin, "events", "manage")
    _grant_permission(admin, "events", "view")

    guardian_user = User.objects.create_user(
        username="ev_guardian",
        password="Password123!",
        phone="+8801711000011",
        institution=inst,
        user_type=UserType.GUARDIAN,
    )
    student = Student.objects.create(
        institution=inst,
        student_id="STU-EV-001",
        name_en="Tanvir Hasan",
        name_bn="তানভীর হাসান",
        dob=date(2012, 3, 15),
        gender="male",
        admission_date=date(2024, 1, 10),
        emergency_contact_name="Hasan Ali",
        emergency_contact_phone="+8801711000011",
    )
    return {
        "inst": inst,
        "other_inst": other_inst,
        "admin": admin,
        "guardian_user": guardian_user,
        "student": student,
    }


@pytest.mark.django_db
def test_unified_calendar_merges_events_holidays_and_notices_tenant_scoped(events_env):
    inst = events_env["inst"]
    other_inst = events_env["other_inst"]
    now = timezone.now()

    Event.objects.create(
        institution=inst,
        title_en="Annual Sports Day",
        title_bn="বার্ষিক ক্রীড়া দিবস",
        category=EventCategory.SPORTS,
        start_datetime=now + timedelta(days=2),
        end_datetime=now + timedelta(days=2, hours=4),
        venue="Main Ground",
        is_published=True,
    )
    Event.objects.create(
        institution=other_inst,
        title_en="Other Tenant Event",
        category=EventCategory.SPORTS,
        start_datetime=now + timedelta(days=2),
        end_datetime=now + timedelta(days=2, hours=2),
        is_published=True,
    )
    Holiday.objects.create(
        institution=inst,
        name="Independence Day",
        type=HolidayType.GOVT,
        start_date=date.today() + timedelta(days=3),
        end_date=date.today() + timedelta(days=3),
    )
    Notice.objects.create(
        institution=inst,
        title_en="Sports Dress Code",
        title_bn="ক্রীড়া পোশাক",
        content_en="Wear house jersey.",
        content_bn="হাউস জার্সি পরুন।",
        category=NoticeCategory.GENERAL,
        target_audience=NoticeAudience.ALL,
        is_published=True,
        publish_date=now,
        created_by=events_env["admin"],
    )

    client = APIClient()
    client.force_authenticate(user=events_env["guardian_user"])
    start_str = (date.today() - timedelta(days=1)).isoformat()
    end_str = (date.today() + timedelta(days=10)).isoformat()

    resp = client.get(f"/api/v1/events/calendar/?start_date={start_str}&end_date={end_str}")
    assert resp.status_code == 200
    titles = [item["title_en"] for item in resp.data]
    source_types = {item["source_type"] for item in resp.data}

    assert "Annual Sports Day" in titles
    assert "Independence Day" in titles
    assert "Sports Dress Code" in titles
    assert "Other Tenant Event" not in titles
    assert source_types == {"event", "holiday", "notice"}


@pytest.mark.django_db
def test_notice_read_receipt_idempotent_and_summary(events_env):
    inst = events_env["inst"]
    notice = Notice.objects.create(
        institution=inst,
        title_en="Exam Schedule",
        title_bn="পরীক্ষার সময়সূচী",
        content_en="Starts next week.",
        content_bn="আগামী সপ্তাহে শুরু।",
        category=NoticeCategory.EXAM,
        target_audience=NoticeAudience.ALL,
        is_published=True,
        publish_date=timezone.now(),
        created_by=events_env["admin"],
    )

    guardian_client = APIClient()
    guardian_client.force_authenticate(user=events_env["guardian_user"])

    r1 = guardian_client.post(
        "/api/v1/events/notice-receipts/mark-read/",
        {"notice": str(notice.id)},
        format="json",
    )
    assert r1.status_code == 201

    r2 = guardian_client.post(
        "/api/v1/events/notice-receipts/mark-read/",
        {"notice": str(notice.id)},
        format="json",
    )
    assert r2.status_code == 200

    # Guardian cannot view admin read summary
    forbidden = guardian_client.get(f"/api/v1/events/notice-receipts/summary/?notice={notice.id}")
    assert forbidden.status_code == 403

    admin_client = APIClient()
    admin_client.force_authenticate(user=events_env["admin"])
    summary = admin_client.get(f"/api/v1/events/notice-receipts/summary/?notice={notice.id}")
    assert summary.status_code == 200
    assert summary.data["total_reads"] == 1


@pytest.mark.django_db
def test_event_rsvp_capacity_enforcement(events_env):
    inst = events_env["inst"]
    now = timezone.now()
    event = Event.objects.create(
        institution=inst,
        title_en="Debate Workshop",
        category=EventCategory.CLUB,
        start_datetime=now + timedelta(days=5),
        end_datetime=now + timedelta(days=5, hours=2),
        requires_rsvp=True,
        max_participants=1,
        is_published=True,
    )

    c1 = APIClient()
    c1.force_authenticate(user=events_env["guardian_user"])
    r1 = c1.post(
        f"/api/v1/events/events/{event.id}/rsvp/",
        {"status": RSVPStatus.GOING, "student": str(events_env["student"].id)},
        format="json",
    )
    assert r1.status_code == 200

    c2 = APIClient()
    c2.force_authenticate(user=events_env["admin"])
    r2 = c2.post(
        f"/api/v1/events/events/{event.id}/rsvp/",
        {"status": RSVPStatus.GOING},
        format="json",
    )
    assert r2.status_code == 400


@pytest.mark.django_db
def test_club_competition_achievement_and_certificate_pdf(events_env):
    inst = events_env["inst"]
    student = events_env["student"]
    club = Club.objects.create(
        institution=inst,
        name_en="Debate Club",
        category=ClubCategory.DEBATE,
    )
    ClubMembership.objects.create(
        institution=inst,
        club=club,
        student=student,
        joined_date=date.today(),
    )
    comp = Competition.objects.create(
        institution=inst,
        club=club,
        title_en="Inter-House Debate 2026",
        competition_date=date.today(),
        level=CompetitionLevel.SCHOOL,
    )
    result = CompetitionResult.objects.create(
        institution=inst,
        competition=comp,
        student=student,
        position=CompetitionPosition.FIRST,
        score_or_remark="Best Speaker",
    )
    achievement = Achievement.objects.create(
        institution=inst,
        student=student,
        title_en="1st Place - Inter-House Debate",
        achieved_date=date.today(),
        competition_result=result,
        description="Winner of annual school debate.",
    )
    cert = Certificate.objects.create(
        institution=inst,
        student=student,
        achievement=achievement,
        competition_result=result,
        certificate_number="CERT-2026-001",
        title_en="Champion - Inter-House Debate 2026",
        issued_date=date.today(),
        signatory_name="Md. Karim",
        signatory_title="Head Teacher",
    )

    client = APIClient()
    client.force_authenticate(user=events_env["admin"])
    resp = client.get(f"/api/v1/events/certificates/{cert.id}/download-pdf/")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/tmp/sms_test_media")
def test_gallery_student_consent_privacy_gating(events_env):
    inst = events_env["inst"]
    album = Album.objects.create(
        institution=inst,
        title_en="Science Fair 2026",
        album_date=date.today(),
        is_published=True,
        is_public_to_guardians=True,
    )
    # Student photo WITHOUT consent
    unconsented = GalleryMedia.objects.create(
        institution=inst,
        album=album,
        media_type=GalleryMediaType.PHOTO,
        file=SimpleUploadedFile("student_no_consent.jpg", b"fakejpg", content_type="image/jpeg"),
        caption_en="Unconsented student photo",
        contains_students=True,
        guardian_consent_verified=False,
        is_approved=True,
    )
    # Student photo WITH consent & approval
    consented = GalleryMedia.objects.create(
        institution=inst,
        album=album,
        media_type=GalleryMediaType.PHOTO,
        file=SimpleUploadedFile("student_consented.jpg", b"fakejpg", content_type="image/jpeg"),
        caption_en="Consented student photo",
        contains_students=True,
        guardian_consent_verified=True,
        is_approved=True,
    )
    # Campus photo (no students) & approved
    campus = GalleryMedia.objects.create(
        institution=inst,
        album=album,
        media_type=GalleryMediaType.PHOTO,
        file=SimpleUploadedFile("campus.png", b"fakepng", content_type="image/png"),
        caption_en="Campus stage",
        contains_students=False,
        guardian_consent_verified=False,
        is_approved=True,
    )

    guardian_client = APIClient()
    guardian_client.force_authenticate(user=events_env["guardian_user"])
    g_resp = guardian_client.get("/api/v1/events/gallery-media/")
    assert g_resp.status_code == 200
    visible_ids = {item["id"] for item in g_resp.data["results"]}
    assert str(unconsented.id) not in visible_ids
    assert str(consented.id) in visible_ids
    assert str(campus.id) in visible_ids

    # Guardian cannot create gallery media
    forbidden_create = guardian_client.post(
        "/api/v1/events/albums/", {"title_en": "Hack"}, format="json"
    )
    assert forbidden_create.status_code == 403
