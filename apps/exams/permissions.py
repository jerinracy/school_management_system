"""Role-based permissions for exam configurations, schedules, and mark entries."""

from apps.accounts.permissions import HasModulePermission

CanViewExams = HasModulePermission("exams.view")
CanManageExams = HasModulePermission("exams.manage")
CanEnterMarks = HasModulePermission("exams.enter_marks")
CanLockMarks = HasModulePermission("exams.lock_marks")
