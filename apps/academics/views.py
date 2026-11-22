"""Views and viewsets for academic structure and routines."""

from typing import Any

from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
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
    AssignClassTeacherSerializer,
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
from apps.accounts.models import UserType
from apps.accounts.permissions import HasModulePermission
from apps.core.mixins import TenantScopedMixin, get_request_institution
from apps.core.pagination import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(summary="List class levels", tags=["Academics"]),
    create=extend_schema(summary="Create a class level", tags=["Academics"]),
    retrieve=extend_schema(summary="Get class level details", tags=["Academics"]),
    update=extend_schema(summary="Update a class level", tags=["Academics"]),
    partial_update=extend_schema(summary="Partially update a class level", tags=["Academics"]),
    destroy=extend_schema(summary="Delete a class level", tags=["Academics"]),
)
class ClassLevelViewSet(TenantScopedMixin, ModelViewSet):
    queryset = ClassLevel.objects.select_related("shift", "session", "branch").all()
    serializer_class = ClassLevelSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_classlevel")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["medium", "has_groups", "shift", "session", "branch"]
    search_fields = ["name", "code"]
    ordering_fields = ["order", "name"]
    ordering = ["order"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasModulePermission("academics.view_classlevel")()]

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        shift_id = self.request.query_params.get("shift")
        if shift_id:
            qs = qs.filter(Q(shift_id=shift_id) | Q(shift__isnull=True))
        session_id = self.request.query_params.get("session")
        if session_id:
            qs = qs.filter(Q(session_id=session_id) | Q(session__isnull=True))
        branch_id = self.request.query_params.get("branch")
        if branch_id:
            qs = qs.filter(Q(branch_id=branch_id) | Q(branch__isnull=True))
        return qs

    def perform_create(self, serializer: Any) -> None:
        institution = get_request_institution(self.request)
        kwargs: dict[str, Any] = {"institution": institution}
        if "shift" not in serializer.validated_data and self.request.data.get("shift"):
            kwargs["shift_id"] = self.request.data.get("shift")
        if "session" not in serializer.validated_data and self.request.data.get("session"):
            kwargs["session_id"] = self.request.data.get("session")
        if "branch" not in serializer.validated_data and self.request.data.get("branch"):
            kwargs["branch_id"] = self.request.data.get("branch")
        serializer.save(**kwargs)


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
        "class_level", "shift", "session", "teacher_user", "teacher_staff"
    ).all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("academics.view_section")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["class_level"]
    search_fields = ["name", "class_level__name"]
    ordering_fields = ["name", "capacity"]
    ordering = ["class_level", "name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve", "teachers", "my_teachers"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasModulePermission("academics.view_section")()]

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        params = getattr(self.request, "query_params", getattr(self.request, "GET", {}))
        branch_id = params.get("branch")
        shift_id = params.get("shift")
        session_id = params.get("session")
        if branch_id:
            qs = qs.filter(
                Q(branch_id=branch_id) | Q(branch__isnull=True, class_level__branch_id=branch_id)
            )
        if shift_id:
            qs = qs.filter(
                Q(shift_id=shift_id) | Q(shift__isnull=True, class_level__shift_id=shift_id)
            )
        if session_id:
            qs = qs.filter(
                Q(session_id=session_id)
                | Q(session__isnull=True, class_level__session_id=session_id)
            )
        if params.get("managed_by_me") in ["true", "1", True] or params.get("class_teacher") in [
            "me",
            "true",
            "1",
        ]:
            if self.request.user.is_authenticated:
                qs = qs.filter(
                    Q(teacher_user=self.request.user) | Q(teacher_staff__user=self.request.user)
                )
            else:
                qs = qs.none()
        elif params.get("teacher_staff"):
            qs = qs.filter(teacher_staff_id=params.get("teacher_staff"))
        elif params.get("teacher_user"):
            qs = qs.filter(teacher_user_id=params.get("teacher_user"))
        return qs

    def perform_create(self, serializer: Any) -> None:
        inst = get_request_institution(self.request)
        class_level = serializer.validated_data.get("class_level")
        branch = serializer.validated_data.get("branch") or (
            class_level.branch if class_level else None
        )
        serializer.save(institution=inst, branch=branch)

    @extend_schema(
        summary="Assign or change Class Teacher for a section",
        request=AssignClassTeacherSerializer,
        responses={200: SectionSerializer},
        tags=["Academics"],
    )
    @action(detail=True, methods=["post"], url_path="assign-class-teacher")
    def assign_class_teacher(self, request: Request, pk: str | None = None) -> Response:
        section = self.get_object()
        serializer = AssignClassTeacherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff_id = serializer.validated_data.get("teacher_staff_id")
        user_id = serializer.validated_data.get("teacher_user_id")

        payload: dict[str, Any] = {}
        if "teacher_staff_id" in request.data:
            payload["teacher_staff"] = staff_id
        if "teacher_user_id" in request.data:
            payload["teacher_user"] = user_id

        sec_serializer = SectionSerializer(
            instance=section,
            data=payload,
            partial=True,
            context={"request": request},
        )
        sec_serializer.is_valid(raise_exception=True)
        sec_serializer.save()
        return Response(sec_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List teachers assigned to routine slots for this section",
        responses={200: OpenApiTypes.OBJECT},
        tags=["Academics"],
    )
    def _build_section_teachers_response(self, section: Section) -> list[dict[str, Any]]:
        from apps.academics.models import RoutineSlot

        slots = (
            RoutineSlot.objects.filter(section=section)
            .select_related(
                "subject", "teacher_staff", "teacher_staff__designation", "teacher_user"
            )
            .order_by("subject__name_en")
        )

        teachers_map: dict[str, dict[str, Any]] = {}

        if section.teacher_staff:
            ts = section.teacher_staff
            t_id = str(ts.id)
            desig = (
                str(
                    ts.designation.title_en
                    if hasattr(ts.designation, "title_en")
                    else ts.designation
                )
                if ts.designation
                else "Class Teacher"
            )
            phone = ts.phone or (ts.user.phone if ts.user else "")
            teachers_map[t_id] = {
                "staff_id": str(ts.id),
                "user_id": str(ts.user_id) if ts.user_id else None,
                "name_en": ts.full_name_en or "Class Teacher",
                "name_bn": getattr(ts, "full_name_bn", "") or "",
                "designation": desig,
                "phone": phone or "",
                "is_class_teacher": True,
                "subjects": [],
            }

        for slot in slots:
            staff = slot.teacher_staff
            user = slot.teacher_user
            if not staff and not user:
                continue

            key = str(staff.id) if staff else f"user_{user.id}"
            if key not in teachers_map:
                name = (
                    (staff.full_name_en or staff.full_name_bn)
                    if staff
                    else (user.full_name or user.username or user.phone)
                )
                desig = (
                    str(
                        staff.designation.title_en
                        if hasattr(staff.designation, "title_en")
                        else staff.designation
                    )
                    if staff and staff.designation
                    else "Subject Teacher"
                )
                phone = staff.phone if (staff and staff.phone) else (user.phone if user else "")
                teachers_map[key] = {
                    "staff_id": str(staff.id) if staff else None,
                    "user_id": (
                        str(staff.user_id)
                        if (staff and staff.user_id)
                        else (str(user.id) if user else None)
                    ),
                    "name_en": name or "Subject Teacher",
                    "name_bn": getattr(staff, "full_name_bn", "") if staff else "",
                    "designation": desig,
                    "phone": phone or "",
                    "is_class_teacher": bool(
                        (staff and section.teacher_staff_id == staff.id)
                        or (user and section.teacher_user_id == user.id)
                    ),
                    "subjects": [],
                }

            subj_name = slot.subject.name_en if slot.subject else ""
            if subj_name and subj_name not in teachers_map[key]["subjects"]:
                teachers_map[key]["subjects"].append(subj_name)

        return list(teachers_map.values())

    @extend_schema(
        summary="List teachers assigned to routine slots for this section",
        responses={200: OpenApiTypes.OBJECT},
        tags=["Academics"],
    )
    @action(detail=True, methods=["get"], url_path="teachers")
    def teachers(self, request: Request, pk: str | None = None) -> Response:
        import uuid

        if pk:
            try:
                uuid.UUID(str(pk))
            except (ValueError, TypeError, AttributeError):
                return self.my_teachers(request)

        try:
            section = self.get_object()
        except Exception:
            return self.my_teachers(request)

        return Response(self._build_section_teachers_response(section))

    @extend_schema(
        summary="List teachers assigned to routine slots for current student's section",
        responses={200: OpenApiTypes.OBJECT},
        tags=["Academics"],
    )
    @action(detail=False, methods=["get"], url_path="my-teachers")
    def my_teachers(self, request: Request) -> Response:
        import uuid

        def _is_valid_uuid(val: Any) -> bool:
            if not val:
                return False
            try:
                uuid.UUID(str(val))
                return True
            except (ValueError, TypeError, AttributeError):
                return False

        institution = get_request_institution(request)
        sec_id = request.query_params.get("section") or request.query_params.get("section_id")
        std_id = request.query_params.get("student") or request.query_params.get("student_id")
        user = request.user

        if sec_id and not _is_valid_uuid(sec_id):
            sec_id = None
        if std_id and not _is_valid_uuid(std_id):
            std_id = None

        if not sec_id and std_id:
            from apps.students.models import StudentEnrollment

            enr = (
                StudentEnrollment.objects.filter(
                    student_id=std_id,
                    institution=institution,
                    status="active",
                )
                .select_related("section")
                .order_by("-session__start_date")
                .first()
            )
            if enr:
                sec_id = enr.section_id

        if not sec_id and user and user.is_authenticated:
            from apps.guardians.models import StudentGuardian
            from apps.students.models import StudentEnrollment

            # 1. Direct student user profile link
            enr = (
                StudentEnrollment.objects.filter(
                    student__user_id=user.id,
                    institution=institution,
                    status="active",
                )
                .select_related("section")
                .order_by("-session__start_date")
                .first()
            )
            if enr:
                sec_id = enr.section_id

            # 2. Student matched by phone
            if not sec_id and getattr(user, "phone", None):
                enr = (
                    StudentEnrollment.objects.filter(
                        student__phone=user.phone,
                        institution=institution,
                        status="active",
                    )
                    .select_related("section")
                    .order_by("-session__start_date")
                    .first()
                )
                if enr:
                    sec_id = enr.section_id

            # 3. Guardian user linked
            if not sec_id:
                sg = (
                    StudentGuardian.objects.filter(
                        guardian__user_id=user.id,
                        institution=institution,
                    )
                    .select_related("student")
                    .first()
                )
                if not sg and getattr(user, "phone", None):
                    sg = (
                        StudentGuardian.objects.filter(
                            guardian__phone=user.phone,
                            institution=institution,
                        )
                        .select_related("student")
                        .first()
                    )
                if sg:
                    enr = (
                        StudentEnrollment.objects.filter(
                            student_id=sg.student_id,
                            institution=institution,
                            status="active",
                        )
                        .select_related("section")
                        .order_by("-session__start_date")
                        .first()
                    )
                    if enr:
                        sec_id = enr.section_id

        if not sec_id:
            # Fall back to section with active routine slots, then any section
            target_sec = (
                Section.objects.filter(institution=institution, routine_slots__isnull=False)
                .distinct()
                .first()
                or Section.objects.filter(institution=institution).first()
            )
            if not target_sec:
                return Response([])
            return Response(self._build_section_teachers_response(target_sec))

        section = Section.objects.filter(id=sec_id, institution=institution).first()
        if not section:
            target_sec = (
                Section.objects.filter(institution=institution, routine_slots__isnull=False)
                .distinct()
                .first()
            )
            if target_sec:
                return Response(self._build_section_teachers_response(target_sec))
            return Response([])
        return Response(self._build_section_teachers_response(section))

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
        branch = data.get("branch") or data["class_level"].branch
        with transaction.atomic():
            for name in data["names"]:
                sec, _ = Section.objects.get_or_create(
                    institution=institution,
                    class_level=data["class_level"],
                    shift=data["shift"],
                    session=data["session"],
                    name=name.strip(),
                    defaults={"capacity": data.get("capacity", 50), "branch": branch},
                )
                if not sec.branch and branch:
                    sec.branch = branch
                    sec.save(update_fields=["branch"])
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

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasModulePermission("academics.view_subject")()]

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        params = getattr(self.request, "query_params", getattr(self.request, "GET", {}))
        class_level_id = params.get("class_level")
        section_id = params.get("section")
        if section_id and not class_level_id:
            sec = Section.objects.filter(id=section_id).first()
            if sec:
                class_level_id = sec.class_level_id
        if class_level_id:
            from apps.academics.models import ClassSubject, RoutineSlot

            subject_ids = set(
                ClassSubject.objects.filter(class_level_id=class_level_id).values_list(
                    "subject_id", flat=True
                )
            )
            routine_slot_filter = Q(section__class_level_id=class_level_id)
            if section_id:
                routine_slot_filter |= Q(section_id=section_id)
            routine_subject_ids = set(
                RoutineSlot.objects.filter(routine_slot_filter).values_list("subject_id", flat=True)
            )
            combined_ids = subject_ids.union(routine_subject_ids)
            qs = qs.filter(id__in=combined_ids)
        return qs

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

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasModulePermission("academics.view_classsubject")()]

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

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasModulePermission("academics.view_routineslot")()]

    def get_queryset(self) -> Any:
        if getattr(self, "swagger_fake_view", False):
            return RoutineSlot.objects.none()

        institution = get_request_institution(self.request)
        sec_id = self.request.query_params.get("section_id") or self.request.query_params.get(
            "section"
        )
        t_id = (
            self.request.query_params.get("teacher_id")
            or self.request.query_params.get("teacher")
            or self.request.query_params.get("teacher_staff")
        )
        r_id = self.request.query_params.get("room_id") or self.request.query_params.get("room")
        w_day = self.request.query_params.get("weekday")
        weekday_int = int(w_day) if w_day is not None and str(w_day).isdigit() else None

        user = self.request.user
        std_id = self.request.query_params.get("student_id") or self.request.query_params.get(
            "student"
        )
        if not sec_id and std_id:
            from apps.students.models import StudentEnrollment

            enr = (
                StudentEnrollment.objects.filter(
                    student_id=std_id,
                    institution=institution,
                    status="active",
                )
                .select_related("section")
                .order_by("-session__start_date")
                .first()
            )
            if enr:
                sec_id = enr.section_id

        if not sec_id and user and user.is_authenticated:
            if getattr(user, "user_type", None) == UserType.STUDENT or hasattr(
                user, "student_profile"
            ):
                from apps.students.models import StudentEnrollment

                enr = (
                    StudentEnrollment.objects.filter(
                        student__user_id=user.id,
                        institution=institution,
                        status="active",
                    )
                    .select_related("section")
                    .order_by("-session__start_date")
                    .first()
                )
                if enr:
                    sec_id = enr.section_id

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

        if (
            user
            and user.is_authenticated
            and (
                getattr(user, "user_type", None) == UserType.TEACHER
                or hasattr(user, "staff_profile")
            )
        ):
            return get_routine_for_teacher(
                institution_id=institution.id, teacher_user_id=user.id, weekday=weekday_int
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
            teacher_staff_id=data.get("teacher_staff_id"),
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
        "routine_slot__section__class_level",
        "routine_slot__period",
        "routine_slot__subject",
        "routine_slot__room",
        "original_teacher",
        "original_staff",
        "substitute_teacher",
        "substitute_staff",
    ).all()
    serializer_class = SubstituteAssignmentSerializer
    permission_classes = [
        IsAuthenticated,
        HasModulePermission("academics.view_substituteassignment"),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "slot_date",
        "substitute_teacher",
        "substitute_staff",
        "original_teacher",
        "original_staff",
    ]
    search_fields = [
        "substitute_staff__full_name_en",
        "substitute_staff__full_name_bn",
        "substitute_teacher__full_name",
        "original_staff__full_name_en",
        "original_staff__full_name_bn",
        "original_teacher__full_name",
        "routine_slot__section__name",
        "routine_slot__section__class_level__name",
        "routine_slot__subject__name_en",
        "routine_slot__subject__name_bn",
        "reason",
    ]
    ordering_fields = ["slot_date", "created_at"]
    ordering = ["-slot_date", "-created_at"]

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
