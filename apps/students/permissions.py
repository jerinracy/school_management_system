"""Permissions for Student management."""

from apps.accounts.permissions import HasModulePermission
from apps.guardians.permissions import IsGuardianOfStudent

CanViewStudents = HasModulePermission("students.view")
CanManageStudents = HasModulePermission("students.manage")

__all__ = [
    "CanViewStudents",
    "CanManageStudents",
    "IsGuardianOfStudent",
]
