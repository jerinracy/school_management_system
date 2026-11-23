import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/features/auth/store/authStore";

export function usePermissions(): string[] {
  const user = useAuthStore((s) => s.user);
  return user?.permissions ?? [];
}

export function usePermission(perm?: string): boolean {
  const user = useAuthStore((s) => s.user);
  if (!user || !perm) return !perm;

  // Superadmin, admin, or wildcard permissions bypass
  if (
    user.user_type === "superadmin" ||
    user.user_type === "super_admin" ||
    user.user_type === "admin" ||
    user.permissions?.includes("*")
  ) {
    return true;
  }

  // Teachers are authorized to access exam views and mark entries
  if (
    user.user_type === "teacher" &&
    (perm === "exams.view" || perm === "exams.enter_marks" || perm === "academics.view" || perm === "attendance.view")
  ) {
    return true;
  }

  const permissions = user.permissions ?? [];
  return permissions.includes(perm);
}

interface CanProps {
  perm?: string;
  userTypes?: string[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function Can({ perm, userTypes, children, fallback = null }: CanProps) {
  const user = useAuthStore((s) => s.user);
  const hasPerm = usePermission(perm);

  if (!user) {
    return <>{fallback}</>;
  }

  if (userTypes && userTypes.length > 0 && !userTypes.includes(user.user_type)) {
    return <>{fallback}</>;
  }

  if (!hasPerm) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

interface ProtectedRouteProps {
  children: ReactNode;
  perm?: string;
  userTypes?: string[];
}

export function ProtectedRoute({ children, perm, userTypes }: ProtectedRouteProps) {
  const { isAuthenticated, isRestoring, user } = useAuthStore();
  const location = useLocation();
  const hasPerm = usePermission(perm);

  if (isRestoring) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user.must_change_password && location.pathname !== "/force-change-password") {
    return <Navigate to="/force-change-password" replace />;
  }

  if (userTypes && userTypes.length > 0 && !userTypes.includes(user.user_type)) {
    return <Navigate to="/403" replace />;
  }

  if (!hasPerm) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}
