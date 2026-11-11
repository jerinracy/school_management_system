"""Management command to seed a demo Bangladeshi school with branches, shifts, sessions, and holidays."""

from datetime import date, time
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.institutions.models import (
    AcademicSession,
    Branch,
    EducationBoard,
    Holiday,
    HolidayType,
    Institution,
    InstitutionType,
    MPOStatus,
    SessionStatus,
    Shift,
    ShiftName,
    Term,
)


class Command(BaseCommand):
    help = (
        "Seed demo institution (school) with branch, shifts, 2026 session, terms, and BD holidays."
    )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(self.style.NOTICE("Seeding demo Bangladeshi educational institution..."))

        institution, created = Institution.objects.get_or_create(
            eiin="134567",
            defaults={
                "name_en": "Dhaka Model High School & College",
                "name_bn": "ঢাকা মডেল হাই স্কুল অ্যান্ড কলেজ",
                "mpo_status": MPOStatus.MPO,
                "board": EducationBoard.DHAKA,
                "type": InstitutionType.HIGHER_SECONDARY,
                "division": "Dhaka",
                "district": "Dhaka",
                "upazila": "Dhanmondi",
                "address_line": "House 12, Road 4, Dhanmondi, Dhaka-1205",
                "phone": "+8801711000000",
                "email": "info@dhakamodel.edu.bd",
                "website": "https://dhakamodel.edu.bd",
                "weekend_days": ["friday", "saturday"],
                "settings": {
                    "grading_profile_id": None,
                    "attendance_defaults": {
                        "late_tolerance_minutes": 15,
                        "half_day_minimum_minutes": 180,
                    },
                    "sms_sender_id": "DMHSC",
                    "fee_receipt_prefix": "DMH-",
                    "bangla_digits": True,
                },
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created institution: {institution.name_en}"))
        else:
            self.stdout.write(
                self.style.WARNING(f"Institution already exists: {institution.name_en}")
            )

        # Main Branch
        main_branch, b_created = Branch.objects.get_or_create(
            institution=institution,
            code="MAIN",
            defaults={
                "name": "Main Campus (Dhanmondi)",
                "address": "Dhanmondi, Dhaka",
                "is_main": True,
            },
        )
        if b_created:
            self.stdout.write(self.style.SUCCESS(f"Created branch: {main_branch.name}"))

        # Shifts
        morning_shift, _ = Shift.objects.get_or_create(
            institution=institution,
            branch=main_branch,
            name=ShiftName.MORNING,
            defaults={
                "start_time": time(7, 30),
                "end_time": time(12, 0),
            },
        )
        day_shift, _ = Shift.objects.get_or_create(
            institution=institution,
            branch=main_branch,
            name=ShiftName.DAY,
            defaults={
                "start_time": time(12, 30),
                "end_time": time(17, 0),
            },
        )
        self.stdout.write(self.style.SUCCESS("Created Morning and Day shifts."))

        # 2026 Academic Session
        session, s_created = AcademicSession.objects.get_or_create(
            institution=institution,
            name="2026",
            defaults={
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "is_current": True,
                "status": SessionStatus.ACTIVE,
            },
        )
        if s_created:
            self.stdout.write(
                self.style.SUCCESS(f"Created active academic session: {session.name}")
            )

        # Terms
        terms_data = [
            ("First Term", date(2026, 1, 1), date(2026, 4, 30), 1),
            ("Half-Yearly Exam", date(2026, 5, 1), date(2026, 8, 31), 2),
            ("Annual Exam", date(2026, 9, 1), date(2026, 12, 31), 3),
        ]
        for name, start, end, order in terms_data:
            Term.objects.get_or_create(
                institution=institution,
                session=session,
                order=order,
                defaults={
                    "name": name,
                    "start_date": start,
                    "end_date": end,
                },
            )
        self.stdout.write(self.style.SUCCESS("Created 3 academic terms for 2026."))

        # Public Holidays in Bangladesh (2026)
        bd_holidays = [
            (
                "International Mother Language Day",
                HolidayType.GOVT,
                date(2026, 2, 21),
                date(2026, 2, 21),
            ),
            ("Independence & National Day", HolidayType.GOVT, date(2026, 3, 26), date(2026, 3, 26)),
            (
                "Pohela Boishakh (Bengali New Year)",
                HolidayType.GOVT,
                date(2026, 4, 14),
                date(2026, 4, 14),
            ),
            ("Eid-ul-Fitr Vacation", HolidayType.GOVT, date(2026, 3, 20), date(2026, 3, 24)),
            ("Eid-ul-Adha Vacation", HolidayType.GOVT, date(2026, 5, 27), date(2026, 5, 31)),
            (
                "Durga Puja (Vijaya Dashami)",
                HolidayType.GOVT,
                date(2026, 10, 19),
                date(2026, 10, 21),
            ),
            ("Victory Day", HolidayType.GOVT, date(2026, 12, 16), date(2026, 12, 16)),
        ]

        for name, h_type, start, end in bd_holidays:
            Holiday.objects.get_or_create(
                institution=institution,
                name=name,
                start_date=start,
                defaults={
                    "type": h_type,
                    "end_date": end,
                    "applies_to_all_branches": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded BD public holidays for 2026."))
        self.stdout.write(self.style.SUCCESS("Done! Demo institution is ready."))
