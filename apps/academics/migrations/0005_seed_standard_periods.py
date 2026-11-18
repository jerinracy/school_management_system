from datetime import time
from django.db import migrations


def seed_standard_periods(apps, schema_editor):
    Shift = apps.get_model("institutions", "Shift")
    Period = apps.get_model("academics", "Period")

    morning_slots = [
        ("1st Period", time(7, 45), time(8, 30), 1, False),
        ("2nd Period", time(8, 30), time(9, 15), 2, False),
        ("3rd Period", time(9, 15), time(10, 0), 3, False),
        ("Tiffin Break", time(10, 0), time(10, 30), 4, True),
        ("4th Period", time(10, 30), time(11, 15), 5, False),
        ("5th Period", time(11, 15), time(12, 0), 6, False),
    ]

    day_slots = [
        ("1st Period", time(12, 30), time(13, 15), 1, False),
        ("2nd Period", time(13, 15), time(14, 0), 2, False),
        ("3rd Period", time(14, 0), time(14, 45), 3, False),
        ("Tiffin Break", time(14, 45), time(15, 15), 4, True),
        ("4th Period", time(15, 15), time(16, 0), 5, False),
        ("5th Period", time(16, 0), time(16, 45), 6, False),
    ]

    generic_slots = [
        ("1st Period", time(9, 0), time(9, 45), 1, False),
        ("2nd Period", time(9, 45), time(10, 30), 2, False),
        ("3rd Period", time(10, 30), time(11, 15), 3, False),
        ("Tiffin Break", time(11, 15), time(11, 45), 4, True),
        ("4th Period", time(11, 45), time(12, 30), 5, False),
        ("5th Period", time(12, 30), time(13, 15), 6, False),
    ]

    for shift in Shift.objects.all():
        shift_name = (shift.name or "").lower()
        if "morning" in shift_name:
            template = morning_slots
        elif "day" in shift_name:
            template = day_slots
        else:
            template = generic_slots

        for name, start_t, end_t, order, is_break in template:
            Period.objects.get_or_create(
                institution=shift.institution,
                shift=shift,
                order=order,
                defaults={
                    "name": name,
                    "start_time": start_t,
                    "end_time": end_t,
                    "is_break": is_break,
                },
            )


def reverse_seed_standard_periods(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0004_classlevel_branch_section_branch"),
        ("institutions", "0003_institution_login_background"),
    ]

    operations = [
        migrations.RunPython(seed_standard_periods, reverse_seed_standard_periods),
    ]
