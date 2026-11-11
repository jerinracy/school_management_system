"""Permissions for hardware terminals, device groups, biometric consent, and raw punches."""

from apps.accounts.permissions import HasModulePermission

CanViewDevices = HasModulePermission("devices.view")
CanManageDevices = HasModulePermission("devices.manage")
CanViewPunches = HasModulePermission("punches.view")
CanManagePunches = HasModulePermission("punches.manage")
