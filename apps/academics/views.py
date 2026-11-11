"""Views and viewsets for academic structure and routines."""

from typing import Any

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.academics.models import (
    ClassLevel,
    ClassSubject,
    Group,
    Period,
    Room,
    RoutineSlot,
    Section,
    Subject,
    SubstituteAssignment,
)
from apps.academics.selectors import (
    build_section_timetable_matrix,
    get_routine_for_room,
    get_routine_for_section,
    get_routine_for_teacher,
)
from apps.academics.serializers import (
    BulkCreateSectionsSerializer,
    ClassLevelSerializer,
    ClassSubjectSerializer,
    CopySessionInputSerializer,
    GroupSerializer,
    PeriodSerializer,
    RoomSerializer,
    RoutineSlotSerializer,
    RoutineValidationInputSerializer,
    SectionSerializer,
    SubjectSerializer,
    SubstituteAssignmentSerializer,
)
from apps.academics.services.conflicts import validate_routine_slot_conflicts
from apps.academics.services.copy_session import copy_academic_structure_from_previous_session
from apps.accounts.models import User
from apps.accounts.permissions import HasModulePermission
from apps.core.mixins import TenantScopedMixin
from apps.core.pagination import StandardResultsSetPagination
from apps.institutions.models import Institution


def get_request_institution(request: Request) -> Institution:
    """Helper to extract and type-narrow the user's institution."""
    user = request.user
    if not isinstance(user, User) or not user.institution:
        raise PermissionDenied("User is not associated with an institution.")
    return user.institution


@extend_schema_view(
    list=extend_schema(summary="List class levels", tags=["Academics"]),
    create=extend_schema(summary="Create a class level", tags=["Academics"]),
    retrieve=extend_schema(summary="Get class level details", tags=["Academics"]),
    update=extend_schema(summary="Update a class level", tags=["Academics"]),
    partial_update=extend_schema(summary="Partially update a class level", tags=["Academics"]),
    destroy=extend_schema(summary="Delete a class level", tags=["Academics"]),
)
class ClassLevelViewSet(TenantScopedMixin, ModelViewSet):
    queryset = ClassLevel.objects.all()
    serializer_class = ClassLevelSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_classlevel")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["medium", "has_groups"]
    search_fields = ["name", "code"]
    ordering_fields = ["order", "name"]
    ordering = ["order"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List academic groups", tags=["Academics"]),
    create=extend_schema(summary="Create an academic group", tags=["Academics"]),
    retrieve=extend_schema(summary="Get group details", tags=["Academics"]),
    update=extend_schema(summary="Update an academic group", tags=["Academics"]),
    partial_update=extend_schema(summary="Partially update a group", tags=["Academics"]),
    destroy=extend_schema(summary="Delete an academic group", tags=["Academics"]),
)
class GroupViewSet(TenantScopedMixin, ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_group")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code"]
    ordering = ["name"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List sections", tags=["Academics"]),
    create=extend_schema(summary="Create a section", tags=["Academics"]),
    retrieve=extend_schema(summary="Get section details", tags=["Academics"]),
    update=extend_schema(summary="Update a section", tags=["Academics"]),
    partial_update=extend_schema(summary="Partially update a section", tags=["Academics"]),
    destroy=extend_schema(summary="Delete a section", tags=["Academics"]),
)
class SectionViewSet(TenantScopedMixin, ModelViewSet):
    queryset = Section.objects.select_related(
        "class_level", "shift", "session", "teacher_user"
    ).all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_section")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["class_level", "shift", "session"]
    search_fields = ["name", "class_level__name"]
    ordering_fields = ["name", "capacity"]
    ordering = ["class_level", "name"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))

    @extend_schema(
        summary="Bulk create sections for a class level",
        request=BulkCreateSectionsSerializer,
        responses={201: SectionSerializer(many=True)},
        tags=["Academics"],
    )
    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request: Request) -> Response:
        serializer = BulkCreateSectionsSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        institution = get_request_institution(request)
        created_sections: list[Section] = []
        with transaction.atomic():
            for name in data["names"]:
                sec, _ = Section.objects.get_or_create(
                    institution=institution,
                    class_level=data["class_level"],
                    shift=data["shift"],
                    session=data["session"],
                    name=name.strip(),
                    defaults={"capacity": data.get("capacity", 50)},
                )
                created_sections.append(sec)

        output_serializer = SectionSerializer(created_sections, many=True)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Get full timetable grid for a section",
        responses={200: dict},
        tags=["Academics"],
    )
    @action(detail=True, methods=["get"], url_path="timetable")
    def timetable(self, request: Request, pk: str | None = None) -> Response:
        section = self.get_object()
        matrix = build_section_timetable_matrix(
            institution_id=get_request_institution(request).id,
            section_id=section.id,
        )
        return Response(matrix, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List subjects", tags=["Academics"]),
    create=extend_schema(summary="Create a subject", tags=["Academics"]),
    retrieve=extend_schema(summary="Get subject details", tags=["Academics"]),
    update=extend_schema(summary="Update a subject", tags=["Academics"]),
    partial_update=extend_schema(summary="Partially update a subject", tags=["Academics"]),
    destroy=extend_schema(summary="Delete a subject", tags=["Academics"]),
)
class SubjectViewSet(TenantScopedMixin, ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_subject")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["type", "has_papers"]
    search_fields = ["name_en", "name_bn", "code"]
    ordering_fields = ["code", "name_en"]
    ordering = ["code"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List class subject offerings", tags=["Academics"]),
    create=extend_schema(summary="Assign subject to class and session", tags=["Academics"]),
    retrieve=extend_schema(summary="Get class subject offering details", tags=["Academics"]),
    update=extend_schema(summary="Update class subject offering", tags=["Academics"]),
    partial_update=extend_schema(
        summary="Partially update class subject offering", tags=["Academics"]
    ),
    destroy=extend_schema(summary="Delete class subject offering", tags=["Academics"]),
)
class ClassSubjectViewSet(TenantScopedMixin, ModelViewSet):
    queryset = ClassSubject.objects.select_related(
        "class_level", "group", "session", "subject"
    ).all()
    serializer_class = ClassSubjectSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_classsubject")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["class_level", "group", "session", "is_optional_elective"]
    ordering_fields = ["class_level", "subject"]
    ordering = ["class_level", "subject"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List rooms", tags=["Academics"]),
    create=extend_schema(summary="Create a room", tags=["Academics"]),
    retrieve=extend_schema(summary="Get room details", tags=["Academics"]),
    update=extend_schema(summary="Update a room", tags=["Academics"]),
    partial_update=extend_schema(summary="Partially update a room", tags=["Academics"]),
    destroy=extend_schema(summary="Delete a room", tags=["Academics"]),
)
class RoomViewSet(TenantScopedMixin, ModelViewSet):
    queryset = Room.objects.select_related("branch").all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_room")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["branch", "type"]
    search_fields = ["name"]
    ordering_fields = ["name", "capacity"]
    ordering = ["branch", "name"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List periods", tags=["Academics"]),
    create=extend_schema(summary="Create a period", tags=["Academics"]),
    retrieve=extend_schema(summary="Get period details", tags=["Academics"]),
    update=extend_schema(summary="Update a period", tags=["Academics"]),
    partial_update=extend_schema(summary="Partially update a period", tags=["Academics"]),
    destroy=extend_schema(summary="Delete a period", tags=["Academics"]),
)
class PeriodViewSet(TenantScopedMixin, ModelViewSet):
    queryset = Period.objects.select_related("shift").all()
    serializer_class = PeriodSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_period")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["shift", "is_break"]
    ordering_fields = ["shift", "order"]
    ordering = ["shift", "order"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(
        summary="List routine slots (by section, teacher, or room)",
        parameters=[
            OpenApiParameter("section_id", str, description="Filter by section UUID"),
            OpenApiParameter("teacher_id", str, description="Filter by teacher user UUID"),
            OpenApiParameter("room_id", str, description="Filter by room UUID"),
            OpenApiParameter(
                "weekday", int, description="Filter by weekday (0=Saturday..6=Friday)"
            ),
        ],
        tags=["Academics"],
    ),
    create=extend_schema(
        summary="Create a routine slot with conflict validation", tags=["Academics"]
    ),
    retrieve=extend_schema(summary="Get routine slot details", tags=["Academics"]),
    update=extend_schema(
        summary="Update routine slot with conflict validation", tags=["Academics"]
    ),
    partial_update=extend_schema(summary="Partially update routine slot", tags=["Academics"]),
    destroy=extend_schema(summary="Delete a routine slot", tags=["Academics"]),
)
class RoutineSlotViewSet(TenantScopedMixin, ModelViewSet):
    queryset = RoutineSlot.objects.select_related(
        "section",
        "section__class_level",
        "period",
        "subject",
        "teacher_user",
        "room",
    ).all()
    serializer_class = RoutineSlotSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_routineslot")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["weekday", "section", "teacher_user", "room"]
    ordering_fields = ["weekday", "period__order"]
    ordering = ["weekday", "period__order"]

    def get_queryset(self) -> Any:
        if getattr(self, "swagger_fake_view", False):
            return RoutineSlot.objects.none()

        institution = get_request_institution(self.request)
        sec_id = self.request.query_params.get("section_id")
        t_id = self.request.query_params.get("teacher_id")
        r_id = self.request.query_params.get("room_id")
        w_day = self.request.query_params.get("weekday")
        weekday_int = int(w_day) if w_day is not None and w_day.isdigit() else None

        if sec_id:
            return get_routine_for_section(
                institution_id=institution.id, section_id=sec_id, weekday=weekday_int
            )
        if t_id:
            return get_routine_for_teacher(
                institution_id=institution.id, teacher_user_id=t_id, weekday=weekday_int
            )
        if r_id:
            return get_routine_for_room(
                institution_id=institution.id, room_id=r_id, weekday=weekday_int
            )

        return super().get_queryset()

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))

    @extend_schema(
        summary="Validate proposed routine slot for conflicts without saving",
        request=RoutineValidationInputSerializer,
        responses={200: dict},
        tags=["Academics"],
    )
    @action(detail=False, methods=["post"], url_path="validate")
    def validate_slot(self, request: Request) -> Response:
        serializer = RoutineValidationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report = validate_routine_slot_conflicts(
            institution_id=get_request_institution(request).id,
            section_id=data["section_id"],
            weekday=data["weekday"],
            period_id=data["period_id"],
            teacher_user_id=data.get("teacher_user_id"),
            room_id=data.get("room_id"),
            exclude_slot_id=data.get("exclude_slot_id"),
        )
        return Response(report.to_dict(), status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List teacher substitute assignments", tags=["Academics"]),
    create=extend_schema(summary="Create a teacher substitute assignment", tags=["Academics"]),
    retrieve=extend_schema(summary="Get substitute assignment details", tags=["Academics"]),
    update=extend_schema(summary="Update a substitute assignment", tags=["Academics"]),
    partial_update=extend_schema(
        summary="Partially update substitute assignment", tags=["Academics"]
    ),
    destroy=extend_schema(summary="Delete a substitute assignment", tags=["Academics"]),
)
class SubstituteAssignmentViewSet(TenantScopedMixin, ModelViewSet):
    queryset = SubstituteAssignment.objects.select_related(
        "routine_slot",
        "routine_slot__section",
        "original_teacher",
        "substitute_teacher",
    ).all()
    serializer_class = SubstituteAssignmentSerializer
    permission_classes = [
        IsAuthenticated,
        HasModulePermission("academics.view_substituteassignment"),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["slot_date", "substitute_teacher", "original_teacher"]
    ordering_fields = ["slot_date"]
    ordering = ["-slot_date"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


class CopySessionView(APIView):
    """API endpoint to copy academic structure from previous session (preview or commit)."""

    permission_classes = [IsAuthenticated, HasModulePermission("academics.change_classlevel")]

    @extend_schema(
        summary="Copy academic structure from previous session (preview or execute)",
        request=CopySessionInputSerializer,
        responses={200: dict},
        tags=["Academics"],
    )
    def post(self, request: Request) -> Response:
        serializer = CopySessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = copy_academic_structure_from_previous_session(
            institution_id=get_request_institution(request).id,
            source_session_id=data["source_session_id"],
            target_session_id=data["target_session_id"],
            copy_sections=data["copy_sections"],
            copy_class_subjects=data["copy_class_subjects"],
            copy_routine=data["copy_routine"],
            preserve_teachers=data["preserve_teachers"],
            dry_run=data["dry_run"],
        )
        return Response(result.to_dict(), status=status.HTTP_200_OK)
