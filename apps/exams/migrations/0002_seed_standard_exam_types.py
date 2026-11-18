from django.db import migrations


def seed_standard_exam_types(apps, schema_editor):
    Institution = apps.get_model("institutions", "Institution")
    ExamType = apps.get_model("exams", "ExamType")

    standard_types = [
        ("Class Assessment / Test", "CT", False, "Continuous assessment and classroom unit tests"),
        ("Half-Yearly Examination", "HY", False, "Mid-year semester summative evaluation"),
        ("Annual Examination", "ANNUAL", False, "Final year-end promotional examination"),
        (
            "Pre-Test Examination",
            "PRE_TEST",
            False,
            "Preliminary qualifying evaluation for senior grades",
        ),
        (
            "Test Examination",
            "TEST",
            True,
            "National board registration qualification examination (SSC/HSC)",
        ),
        (
            "Model Test",
            "MODEL_TEST",
            True,
            "Simulated examination matching national education board patterns",
        ),
    ]

    for inst in Institution.objects.all():
        for name, code, is_board, desc in standard_types:
            ExamType.objects.get_or_create(
                institution=inst,
                code=code,
                defaults={
                    "name": name,
                    "is_board_exam": is_board,
                    "description": desc,
                },
            )


def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0001_initial"),
        ("institutions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_standard_exam_types, reverse_seed),
    ]
