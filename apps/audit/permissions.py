"""RBAC permissions for Audit Logging & Activity Tracking."""

from apps.accounts.permissions import HasModulePermission

CanViewAudit = HasModulePermission("audit.view")
