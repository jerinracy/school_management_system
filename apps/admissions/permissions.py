"""Admissions permissions."""

from apps.accounts.permissions import HasModulePermission

CanManageAdmissions = HasModulePermission("admissions.change_application")
CanViewAdmissions = HasModulePermission("admissions.view_application")
