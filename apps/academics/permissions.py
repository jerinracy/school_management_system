"""Academics permissions."""

from apps.accounts.permissions import HasModulePermission

CanManageAcademics = HasModulePermission("academics.change_classlevel")
CanViewAcademics = HasModulePermission("academics.view_classlevel")
