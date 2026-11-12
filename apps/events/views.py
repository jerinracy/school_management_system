"""DRF Views & ViewSets for Notice Board receipts, Unified Calendar, Events, Clubs, Certificates & Gallery."""

from datetime import date, timedelta
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, QuerySet
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.communications.models import Notice
from apps.core.mixins import TenantScopedMixin
from apps.events.models import (
    Achievement,
    Album,
    Certificate,
    Club,
    ClubMembership,
    Competition,
    CompetitionResult,
    Event,
    GalleryMedia,
    NoticeReadReceipt,
)
from apps.events.permissions import (
    CanManageEventsOnly,
    CanReadOrManageEvents,
    has_events_manage_permission,
    has_events_staff_permission,
    resolve_guardian_ward_ids,
    resolve_student_for_user,
)
from apps.events.serializers import (
    AchievementSerializer,
    AlbumSerializer,
    CertificateSerializer,
    ClubMembershipSerializer,
    ClubSerializer,
    CompetitionResultSerializer,
    CompetitionSerializer,
    EventRSVPActionSerializer,
    EventRSVPSerializer,
    EventSerializer,
    GalleryMediaSerializer,
    MarkNoticeReadSerializer,
    NoticeReadReceiptSerializer,
    UnifiedCalendarItemSerializer,
)
from apps.events.services import (
    generate_certificate_pdf,
    get_notice_read_summary,
    get_unified_calendar,
    mark_notice_as_read,
    rsvp_to_event,
)
from apps.students.models import Student


class UnifiedCalendarView(APIView):
    """Unified chronological calendar merging Events, Holidays, and published Notices."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: UnifiedCalendarItemSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        institution = getattr(request, "institution", None) or getattr(
            request.user, "institution", None
        )
        if institution is None:
            return Response({"detail": "Institution context required."}, status=400)

        today = date.today()
        raw_start = request.query_params.get("start_date")
        raw_end = request.query_params.get("end_date")
        try:
            start_date = date.fromisoformat(raw_start) if raw_start else today - timedelta(days=7)
            end_date = date.fromisoformat(raw_end) if raw_end else start_date + timedelta(days=37)
        except ValueError as exc:
            raise DRFValidationError({"detail": "Invalid date format. Use YYYY-MM-DD."}) from exc

        include_unpublished = has_events_manage_permission(request, self)
        try:
            items = get_unified_calendar(
                institution=institution,
                start_date=start_date,
                end_date=end_date,
                include_unpublished=include_unpublished,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages) from exc

        return Response(items, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List notice read receipts"),
    retrieve=extend_schema(summary="Retrieve a notice read receipt"),
)
class NoticeReadReceiptViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Notice read receipt tracking and read-summary endpoints."""

    queryset = NoticeReadReceipt.objects.select_related("notice", "user")
    serializer_class = NoticeReadReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[NoticeReadReceipt]:
        qs = super().get_queryset()
        user = self.request.user
        if not isinstance(user, User):
            return qs.none()
        if has_events_staff_permission(self.request, self):
            return qs
        return qs.filter(user=user)

    @extend_schema(
        request=MarkNoticeReadSerializer,
        responses={200: NoticeReadReceiptSerializer},
    )
    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request: Request) -> Response:
        serializer = MarkNoticeReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not isinstance(user, User):
            return Response({"detail": "Authentication required."}, status=401)
        institution = getattr(request, "institution", None) or user.institution
        if institution is None:
            return Response({"detail": "Institution context required."}, status=400)

        notice = Notice.objects.filter(
            id=serializer.validated_data["notice"],
            institution=institution,
            is_deleted=False,
        ).first()
        if notice is None:
            return Response({"detail": "Notice not found."}, status=404)

        receipt, created = mark_notice_as_read(
            institution=institution,
            notice=notice,
            user=user,
        )
        return Response(
            NoticeReadReceiptSerializer(receipt).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="notice",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ]
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="summary",
        permission_classes=[IsAuthenticated, CanManageEventsOnly],
    )
    def summary(self, request: Request) -> Response:
        notice_id = request.query_params.get("notice")
        if not notice_id:
            raise DRFValidationError({"notice": "Query parameter 'notice' is required."})
        institution = getattr(request, "institution", None) or getattr(
            request.user, "institution", None
        )
        if institution is None:
            return Response({"detail": "Institution context required."}, status=400)
        notice = Notice.objects.filter(
            id=notice_id,
            institution=institution,
            is_deleted=False,
        ).first()
        if notice is None:
            return Response({"detail": "Notice not found."}, status=404)
        return Response(get_notice_read_summary(institution=institution, notice=notice))


class EventViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for school & club events plus RSVP action."""

    queryset = Event.objects.select_related("club", "organizer", "target_class_level")
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["category", "is_published", "requires_rsvp", "club"]
    search_fields = ["title_en", "title_bn", "venue"]

    def get_queryset(self) -> QuerySet[Event]:
        qs = super().get_queryset().filter(is_deleted=False)
        if not has_events_staff_permission(self.request, self):
            qs = qs.filter(is_published=True)
        return qs

    @extend_schema(request=EventRSVPActionSerializer, responses={200: EventRSVPSerializer})
    @action(
        detail=True,
        methods=["post"],
        url_path="rsvp",
        permission_classes=[IsAuthenticated],
    )
    def rsvp(self, request: Request, pk: Any = None) -> Response:
        event = self.get_object()
        serializer = EventRSVPActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not isinstance(user, User):
            return Response({"detail": "Authentication required."}, status=401)
        institution = getattr(request, "institution", None) or user.institution
        if institution is None:
            return Response({"detail": "Institution context required."}, status=400)

        student_id = serializer.validated_data.get("student")
        student = None
        if student_id:
            student = Student.objects.filter(
                id=student_id,
                institution=institution,
                is_deleted=False,
            ).first()
            if student is None:
                raise DRFValidationError({"student": "Student not found in this institution."})

        try:
            rsvp_obj = rsvp_to_event(
                institution=institution,
                event=event,
                user=user,
                status=serializer.validated_data["status"],
                student=student,
                note=serializer.validated_data.get("note", ""),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc

        return Response(EventRSVPSerializer(rsvp_obj).data, status=status.HTTP_200_OK)


class ClubViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Club.objects.select_related("advisor")
    serializer_class = ClubSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["category", "is_active"]
    search_fields = ["name_en", "name_bn"]

    def get_queryset(self) -> QuerySet[Club]:
        return super().get_queryset().filter(is_deleted=False)


class ClubMembershipViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = ClubMembership.objects.select_related("club", "student")
    serializer_class = ClubMembershipSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["club", "student", "role", "status"]

    def get_queryset(self) -> QuerySet[ClubMembership]:
        qs = super().get_queryset().filter(is_deleted=False)
        if has_events_staff_permission(self.request, self):
            return qs
        student = resolve_student_for_user(self.request.user)
        if student:
            return qs.filter(student=student)
        ward_ids = resolve_guardian_ward_ids(self.request.user)
        if ward_ids:
            return qs.filter(student_id__in=ward_ids)
        return qs.none()


class CompetitionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Competition.objects.select_related("event", "club")
    serializer_class = CompetitionSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["level", "club", "event"]
    search_fields = ["title_en", "title_bn"]

    def get_queryset(self) -> QuerySet[Competition]:
        return super().get_queryset().filter(is_deleted=False)


class CompetitionResultViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = CompetitionResult.objects.select_related("competition", "student")
    serializer_class = CompetitionResultSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["competition", "student", "position"]

    def get_queryset(self) -> QuerySet[CompetitionResult]:
        return super().get_queryset().filter(is_deleted=False)


class AchievementViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Achievement.objects.select_related("student", "competition_result")
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["student", "category", "is_verified"]

    def get_queryset(self) -> QuerySet[Achievement]:
        qs = super().get_queryset().filter(is_deleted=False)
        if has_events_staff_permission(self.request, self):
            return qs
        student = resolve_student_for_user(self.request.user)
        if student:
            return qs.filter(student=student)
        ward_ids = resolve_guardian_ward_ids(self.request.user)
        if ward_ids:
            return qs.filter(student_id__in=ward_ids)
        return qs.none()

    def perform_create(self, serializer: Any) -> None:
        super().perform_create(serializer)
        user = self.request.user
        if isinstance(user, User) and serializer.instance.is_verified:
            serializer.instance.verified_by = user
            serializer.instance.save(update_fields=["verified_by"])


class CertificateViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Certificate.objects.select_related("student", "achievement", "institution")
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["student", "template_code"]
    search_fields = ["certificate_number", "title_en"]

    def get_queryset(self) -> QuerySet[Certificate]:
        qs = super().get_queryset().filter(is_deleted=False)
        if has_events_staff_permission(self.request, self):
            return qs
        student = resolve_student_for_user(self.request.user)
        if student:
            return qs.filter(student=student)
        ward_ids = resolve_guardian_ward_ids(self.request.user)
        if ward_ids:
            return qs.filter(student_id__in=ward_ids)
        return qs.none()

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request: Request, pk: Any = None) -> HttpResponse:
        certificate = self.get_object()
        pdf_bytes = generate_certificate_pdf(certificate)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="certificate-{certificate.certificate_number}.pdf"'
        )
        return response


class AlbumViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Album.objects.select_related("event")
    serializer_class = AlbumSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["event", "is_published", "is_public_to_guardians"]

    def get_queryset(self) -> QuerySet[Album]:
        qs = super().get_queryset().filter(is_deleted=False)
        if not has_events_staff_permission(self.request, self):
            qs = qs.filter(is_published=True, is_public_to_guardians=True)
        return qs


class GalleryMediaViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Gallery media with strict guardian consent gating for student photos/videos."""

    queryset = GalleryMedia.objects.select_related("album")
    serializer_class = GalleryMediaSerializer
    permission_classes = [IsAuthenticated, CanReadOrManageEvents]
    filterset_fields = ["album", "media_type", "is_approved", "guardian_consent_verified"]

    def get_queryset(self) -> QuerySet[GalleryMedia]:
        qs = super().get_queryset().filter(is_deleted=False)
        if not has_events_staff_permission(self.request, self):
            qs = qs.filter(
                album__is_deleted=False,
                album__is_published=True,
                album__is_public_to_guardians=True,
                is_approved=True,
            ).filter(Q(contains_students=False) | Q(guardian_consent_verified=True))
        return qs
