"""DRF ViewSets and Views for institutions module."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import TenantScopedMixin

from .models import AcademicSession, Branch, Holiday, Institution, Shift, Term
from .permissions import IsInstitutionAdminOrReadOnly
from .serializers import (
    AcademicSessionSerializer,
    BranchSerializer,
    HolidaySerializer,
    InstitutionPublicBrandingSerializer,
    InstitutionSerializer,
    SessionCloseSerializer,
    ShiftSerializer,
    TermSerializer,
)
from .services import activate_academic_session, close_academic_session


@extend_schema(tags=["Institution Branding"])
class InstitutionPublicBrandingView(APIView):
    """Retrieve public identity, logo, and metadata for the institution."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get Public Institution Branding",
        description="Returns school name (Bangla/English), logo, EIIN, and contact for login and header displays.",
        parameters=[
            OpenApiParameter(
                name="eiin",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Optional institution EIIN",
            ),
            OpenApiParameter(
                name="institution_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Optional institution UUID",
            ),
        ],
        responses={200: InstitutionPublicBrandingSerializer},
        auth=[],
    )
    def get(self, request: Request) -> Response:
        eiin = request.query_params.get("eiin")
        institution_id = request.query_params.get("institution_id")

        inst = None
        if eiin:
            inst = Institution.objects.filter(eiin=eiin, is_active=True).first()
        elif institution_id:
            inst = Institution.objects.filter(id=institution_id, is_active=True).first()

        if not inst:
            # Fallback to the primary active institution
            inst = Institution.objects.filter(is_active=True).first()

        if not inst:
            # Safe default fallback for unseeded databases
            return Response(
                {
                    "id": None,
                    "name_bn": "বিদ্যালয় ব্যবস্থাপনা পদ্ধতি",
                    "name_en": "School Management System",
                    "eiin": "",
                    "board": "dhaka",
                    "type": "secondary",
                    "logo": None,
                    "logo_url": None,
                    "login_background": None,
                    "login_background_url": None,
                    "phone": "",
                    "email": "",
                    "website": "",
                    "address_line": "",
                    "district": "",
                    "division": "",
                },
                status=status.HTTP_200_OK,
            )

        serializer = InstitutionPublicBrandingSerializer(inst, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Institution Profile"])
class InstitutionProfileView(APIView):
    """Retrieve or update the authenticated user's institution profile."""

    permission_classes = [IsInstitutionAdminOrReadOnly]

    def _get_institution(self, request: Request) -> Institution:
        user = request.user
        institution_id = getattr(user, "institution_id", None)
        if not institution_id and not user.is_superuser:
            raise PermissionDenied("User is not attached to any institution.")

        # If superuser without institution, allow query param ?institution_id=...
        if user.is_superuser and not institution_id:
            institution_id = request.query_params.get("institution_id")
            if not institution_id:
                inst = Institution.objects.first()
                if not inst:
                    raise NotFound("No institutions exist in the system.")
                return inst

        inst = Institution.objects.filter(id=str(institution_id), is_active=True).first()
        if not inst:
            raise NotFound("Institution not found or inactive.")
        return inst

    @extend_schema(
        summary="Get Institution Profile",
        responses={200: InstitutionSerializer},
    )
    def get(self, request: Request) -> Response:
        institution = self._get_institution(request)
        serializer = InstitutionSerializer(institution, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Update Institution Profile",
        request=InstitutionSerializer,
        responses={200: InstitutionSerializer},
    )
    def patch(self, request: Request) -> Response:
        institution = self._get_institution(request)
        serializer = InstitutionSerializer(
            institution, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List Branches", tags=["Branches"]),
    create=extend_schema(summary="Create Branch", tags=["Branches"]),
    retrieve=extend_schema(summary="Get Branch", tags=["Branches"]),
    update=extend_schema(summary="Update Branch", tags=["Branches"]),
    partial_update=extend_schema(summary="Partial Update Branch", tags=["Branches"]),
    destroy=extend_schema(summary="Delete Branch", tags=["Branches"]),
)
class BranchViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD viewset for institution branches."""

    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]
    filterset_fields = ["is_main"]
    search_fields = ["name", "code", "address"]
    ordering_fields = ["name", "code", "created_at"]


@extend_schema_view(
    list=extend_schema(summary="List Shifts", tags=["Shifts"]),
    create=extend_schema(summary="Create Shift", tags=["Shifts"]),
    retrieve=extend_schema(summary="Get Shift", tags=["Shifts"]),
    update=extend_schema(summary="Update Shift", tags=["Shifts"]),
    partial_update=extend_schema(summary="Partial Update Shift", tags=["Shifts"]),
    destroy=extend_schema(summary="Delete Shift", tags=["Shifts"]),
)
class ShiftViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD viewset for branch shifts."""

    queryset = Shift.objects.select_related("branch").all()
    serializer_class = ShiftSerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]
    filterset_fields = ["branch", "name"]
    search_fields = ["branch__code", "name"]
    ordering_fields = ["branch", "start_time"]


@extend_schema_view(
    list=extend_schema(summary="List Academic Sessions", tags=["Academic Sessions"]),
    create=extend_schema(summary="Create Academic Session", tags=["Academic Sessions"]),
    retrieve=extend_schema(summary="Get Academic Session", tags=["Academic Sessions"]),
    update=extend_schema(summary="Update Academic Session", tags=["Academic Sessions"]),
    partial_update=extend_schema(
        summary="Partial Update Academic Session", tags=["Academic Sessions"]
    ),
    destroy=extend_schema(summary="Delete Academic Session", tags=["Academic Sessions"]),
)
class AcademicSessionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD and lifecycle actions for Academic Sessions."""

    queryset = AcademicSession.objects.prefetch_related("terms").all()
    serializer_class = AcademicSessionSerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]
    filterset_fields = ["is_current", "status"]
    search_fields = ["name"]
    ordering_fields = ["start_date", "name"]

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        session = self.get_object()
        if session.is_current:
            raise ValidationError(
                detail="Cannot delete the currently active academic session. Activate another session first."
            )
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Activate Academic Session",
        description="Atomically activates this academic session as the only current session for the tenant.",
        request=None,
        responses={
            200: AcademicSessionSerializer,
            400: OpenApiResponse(description="Cannot activate session."),
        },
        tags=["Academic Sessions"],
    )
    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request: Request, pk: str | None = None) -> Response:
        session = self.get_object()
        try:
            activated = activate_academic_session(
                session_id=session.id,
                institution_id=session.institution_id,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            msg = exc.message if hasattr(exc, "message") else str(exc)
            raise ValidationError(detail=msg) from exc

        serializer = self.get_serializer(activated)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Close Academic Session",
        description="Safely and irreversibly closes an active academic session. Requires confirm=True in payload.",
        request=SessionCloseSerializer,
        responses={
            200: AcademicSessionSerializer,
            400: OpenApiResponse(description="Pre-checks failed."),
        },
        tags=["Academic Sessions"],
    )
    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request: Request, pk: str | None = None) -> Response:
        session = self.get_object()
        close_serializer = SessionCloseSerializer(data=request.data)
        close_serializer.is_valid(raise_exception=True)
        confirm = close_serializer.validated_data["confirm"]

        try:
            closed = close_academic_session(
                session_id=session.id,
                institution_id=session.institution_id,
                confirm=confirm,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            msg = exc.message if hasattr(exc, "message") else str(exc)
            raise ValidationError(detail=msg) from exc

        serializer = self.get_serializer(closed)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List Terms", tags=["Terms"]),
    create=extend_schema(summary="Create Term", tags=["Terms"]),
    retrieve=extend_schema(summary="Get Term", tags=["Terms"]),
    update=extend_schema(summary="Update Term", tags=["Terms"]),
    partial_update=extend_schema(summary="Partial Update Term", tags=["Terms"]),
    destroy=extend_schema(summary="Delete Term", tags=["Terms"]),
)
class TermViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD viewset for academic terms."""

    queryset = Term.objects.select_related("session").all()
    serializer_class = TermSerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]
    filterset_fields = ["session", "order"]
    search_fields = ["name", "session__name"]
    ordering_fields = ["session", "order", "start_date"]


@extend_schema_view(
    list=extend_schema(summary="List Holidays", tags=["Holidays"]),
    create=extend_schema(summary="Create Holiday", tags=["Holidays"]),
    retrieve=extend_schema(summary="Get Holiday", tags=["Holidays"]),
    update=extend_schema(summary="Update Holiday", tags=["Holidays"]),
    partial_update=extend_schema(summary="Partial Update Holiday", tags=["Holidays"]),
    destroy=extend_schema(summary="Delete Holiday", tags=["Holidays"]),
)
class HolidayViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD viewset for institution holidays."""

    queryset = Holiday.objects.prefetch_related("branches").all()
    serializer_class = HolidaySerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]
    filterset_fields = ["type", "applies_to_all_branches"]
    search_fields = ["name", "description"]
    ordering_fields = ["start_date", "end_date"]
