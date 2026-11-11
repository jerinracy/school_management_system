"""Role-based permissions for grading scales, results tabulation, and publications."""

from apps.accounts.permissions import HasModulePermission

CanViewResults = HasModulePermission("results.view")
CanManageGrading = HasModulePermission("results.manage")
CanCalculateResults = HasModulePermission("results.calculate")
CanPublishResults = HasModulePermission("results.publish")
