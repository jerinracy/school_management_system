"""Data migration: backfill superuser and platform admin institution."""

from django.db import migrations


def backfill_superuser_institution(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Institution = apps.get_model("institutions", "Institution")

    default_institution = Institution.objects.first()
    if not default_institution:
        return

    # Backfill superusers and superadmin users missing an institution
    User.objects.filter(institution__isnull=True).filter(is_superuser=True).update(
        institution=default_institution
    )

    User.objects.filter(
        institution__isnull=True, user_type__in=["superadmin", "super_admin"]
    ).update(institution=default_institution)


def rollback_superuser_institution(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("institutions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_superuser_institution, rollback_superuser_institution),
    ]
