# Data migration to link existing superadmins and seed initial staff

from datetime import date
from django.db import migrations


def seed_staff(apps, schema_editor):
    Institution = apps.get_model("institutions", "Institution")
    Department = apps.get_model("staff", "Department")
    Designation = apps.get_model("staff", "Designation")
    Staff = apps.get_model("staff", "Staff")
    User = apps.get_model("accounts", "User")

    inst = Institution.objects.first()
    if not inst:
        return

    # Departments
    admin_dept, _ = Department.objects.get_or_create(
        institution=inst, name="Administration", defaults={"code": "ADMIN"}
    )
    acad_dept, _ = Department.objects.get_or_create(
        institution=inst, name="Academic / Faculty", defaults={"code": "ACAD"}
    )
    acc_dept, _ = Department.objects.get_or_create(
        institution=inst, name="Accounts & Finance", defaults={"code": "ACC"}
    )
    supp_dept, _ = Department.objects.get_or_create(
        institution=inst, name="General Support & Facilities", defaults={"code": "SUPP"}
    )

    # Designations
    superadmin_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Super Admin",
        defaults={
            "title_bn": "সুপার অ্যাডমিন",
            "code": "SA",
            "rank_order": 1,
            "role_category": "superadmin",
        },
    )
    headmaster_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Principal / Headmaster",
        defaults={
            "title_bn": "অধ্যক্ষ / প্রধান শিক্ষক",
            "code": "HM",
            "rank_order": 2,
            "role_category": "admin",
        },
    )
    asst_head_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Assistant Headmaster",
        defaults={
            "title_bn": "সহকারী প্রধান শিক্ষক",
            "code": "AHM",
            "rank_order": 3,
            "role_category": "admin",
        },
    )
    accountant_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Senior Accountant",
        defaults={
            "title_bn": "হিসাবরক্ষক কর্মকর্তা",
            "code": "ACC",
            "rank_order": 4,
            "role_category": "admin",
        },
    )
    sr_teacher_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Senior Teacher",
        defaults={
            "title_bn": "সিনিয়র শিক্ষক",
            "code": "ST",
            "rank_order": 5,
            "role_category": "teacher",
        },
    )
    asst_teacher_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Assistant Teacher",
        defaults={
            "title_bn": "সহকারী শিক্ষক",
            "code": "AT",
            "rank_order": 6,
            "role_category": "teacher",
        },
    )
    office_asst_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Office Assistant",
        defaults={
            "title_bn": "অফিস সহকারী",
            "code": "OA",
            "rank_order": 7,
            "role_category": "support",
        },
    )
    guard_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Security Guard",
        defaults={
            "title_bn": "নিরাপত্তা প্রহরী",
            "code": "SEC",
            "rank_order": 8,
            "role_category": "security",
        },
    )
    driver_desig, _ = Designation.objects.get_or_create(
        institution=inst,
        title="Campus Driver",
        defaults={
            "title_bn": "যানবাহন চালক",
            "code": "DRV",
            "rank_order": 9,
            "role_category": "driver",
        },
    )

    # Link existing users (recy, sifat)
    sifat_user = User.objects.filter(username="sifat").first()
    if sifat_user and not Staff.objects.filter(user=sifat_user).exists():
        Staff.objects.create(
            institution=inst,
            employee_id="EMP-2026-00001",
            full_name_en="Sifat",
            full_name_bn="সিফাত",
            user=sifat_user,
            department=admin_dept,
            designation=superadmin_desig,
            staff_type="superadmin",
            phone=sifat_user.phone or "+8801700000001",
            email=sifat_user.email or "sifat@example.com",
            gender="male",
            dob=date(1995, 1, 1),
            joining_date=date(2026, 1, 1),
            status="active",
        )

    recy_user = User.objects.filter(username="recy").first()
    if recy_user and not Staff.objects.filter(user=recy_user).exists():
        Staff.objects.create(
            institution=inst,
            employee_id="EMP-2026-00002",
            full_name_en="Recy",
            full_name_bn="রেসি",
            user=recy_user,
            department=admin_dept,
            designation=superadmin_desig,
            staff_type="superadmin",
            phone=recy_user.phone or "+8801700000002",
            email=recy_user.email or "recy@example.com",
            gender="female",
            dob=date(1996, 5, 15),
            joining_date=date(2026, 1, 1),
            status="active",
        )

    # Seed baseline Admin staff
    if not Staff.objects.filter(employee_id="EMP-2026-00003").exists():
        Staff.objects.create(
            institution=inst,
            employee_id="EMP-2026-00003",
            full_name_en="Mohammad Rafiqul Islam",
            full_name_bn="মোহাম্মদ রফিকুল ইসলাম",
            department=admin_dept,
            designation=headmaster_desig,
            staff_type="admin",
            phone="+8801711000001",
            email="principal@modelcollege.edu.bd",
            gender="male",
            dob=date(1975, 3, 10),
            joining_date=date(2015, 1, 1),
            status="active",
            is_mpo=True,
            mpo_index_number="MPO-1049281",
        )

    if not Staff.objects.filter(employee_id="EMP-2026-00004").exists():
        Staff.objects.create(
            institution=inst,
            employee_id="EMP-2026-00004",
            full_name_en="Nasrin Sultana",
            full_name_bn="নাসরিন সুলতানা",
            department=admin_dept,
            designation=asst_head_desig,
            staff_type="admin",
            phone="+8801711000002",
            email="nasrin.sultana@modelcollege.edu.bd",
            gender="female",
            dob=date(1980, 8, 20),
            joining_date=date(2018, 6, 1),
            status="active",
            is_mpo=True,
            mpo_index_number="MPO-2094812",
        )

    if not Staff.objects.filter(employee_id="EMP-2026-00005").exists():
        Staff.objects.create(
            institution=inst,
            employee_id="EMP-2026-00005",
            full_name_en="Kamal Hossain",
            full_name_bn="কামাল হোসেন",
            department=acc_dept,
            designation=accountant_desig,
            staff_type="admin",
            phone="+8801711000003",
            email="accounts@modelcollege.edu.bd",
            gender="male",
            dob=date(1985, 11, 5),
            joining_date=date(2020, 2, 1),
            status="active",
        )

    # Seed baseline Teachers
    teachers = [
        (
            "EMP-2026-00006",
            "Anisur Rahman",
            "আনিসুর রহমান",
            sr_teacher_desig,
            "+8801711000004",
            "anisur.rahman@modelcollege.edu.bd",
            "male",
            True,
            "MPO-3019284",
        ),
        (
            "EMP-2026-00007",
            "Farhana Akter",
            "ফারহানা আক্তার",
            sr_teacher_desig,
            "+8801711000005",
            "farhana.akter@modelcollege.edu.bd",
            "female",
            True,
            "MPO-3019285",
        ),
        (
            "EMP-2026-00008",
            "Tanvir Ahmed",
            "তানভীর আহমেদ",
            asst_teacher_desig,
            "+8801711000006",
            "tanvir.ahmed@modelcollege.edu.bd",
            "male",
            False,
            "",
        ),
        (
            "EMP-2026-00009",
            "Roksana Parvin",
            "রোকসানা পারভীন",
            asst_teacher_desig,
            "+8801711000007",
            "roksana.parvin@modelcollege.edu.bd",
            "female",
            False,
            "",
        ),
    ]

    for emp_id, name_en, name_bn, desig, phone, email, gender, is_mpo, mpo_idx in teachers:
        if not Staff.objects.filter(employee_id=emp_id).exists():
            Staff.objects.create(
                institution=inst,
                employee_id=emp_id,
                full_name_en=name_en,
                full_name_bn=name_bn,
                department=acad_dept,
                designation=desig,
                staff_type="teacher",
                phone=phone,
                email=email,
                gender=gender,
                dob=date(1988, 4, 12),
                joining_date=date(2021, 3, 1),
                status="active",
                is_mpo=is_mpo,
                mpo_index_number=mpo_idx,
            )

    # Seed baseline Support Staff
    support_staff = [
        (
            "EMP-2026-00010",
            "Md. Abdul Alim",
            "মোঃ আব্দুল আলিম",
            office_asst_desig,
            "support",
            "+8801711000008",
        ),
        (
            "EMP-2026-00011",
            "Belal Hossain",
            "বেলাল হোসেন",
            guard_desig,
            "security",
            "+8801711000009",
        ),
        ("EMP-2026-00012", "Abul Kashem", "আবুল কাশেম", driver_desig, "driver", "+8801711000010"),
    ]

    for emp_id, name_en, name_bn, desig, s_type, phone in support_staff:
        if not Staff.objects.filter(employee_id=emp_id).exists():
            Staff.objects.create(
                institution=inst,
                employee_id=emp_id,
                full_name_en=name_en,
                full_name_bn=name_bn,
                department=supp_dept,
                designation=desig,
                staff_type=s_type,
                phone=phone,
                gender="male",
                dob=date(1990, 7, 1),
                joining_date=date(2022, 1, 1),
                status="active",
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0002_alter_designation_role_category_and_more"),
        ("accounts", "0001_initial"),
        ("institutions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_staff, noop),
    ]
