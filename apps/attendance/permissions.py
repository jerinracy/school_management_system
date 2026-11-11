"""Role-based permissions for attendance policies, records, and approvals."""

from apps.accounts.permissions import HasModulePermission

CanViewAttendance = HasModulePermission("attendance.view")
CanManageAttendance = HasModulePermission("attendance.manage")
CanTakePeriodAttendance = HasModulePermission("attendance.take_period")
CanApproveCorrection = HasModulePermission("attendance.approve_correction")
