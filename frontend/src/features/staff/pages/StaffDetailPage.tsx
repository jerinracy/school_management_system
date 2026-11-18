import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  ArrowLeft,
  Briefcase,
  Calendar,
  CheckCircle2,
  Clock,
  CreditCard,
  Download,
  Eye,
  EyeOff,
  GraduationCap,
  KeyRound,
  Lock,
  Mail,
  MapPin,
  Phone,
  Shield,
  User,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { useAuthStore } from "@/features/auth/store/authStore";
import { staffApi } from "@/features/staff/api/staffApi";
import { StaffIDCardPreview } from "@/features/staff/components/StaffIDCardPreview";

type DetailTab = "overview" | "assignments" | "leaves" | "idcard";

export default function StaffDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");

  const currentUser = useAuthStore((s) => s.user);
  const isSuper =
    currentUser?.user_type === "superadmin" ||
    currentUser?.user_type === "super_admin" ||
    currentUser?.roles?.includes("superadmin") ||
    currentUser?.roles?.includes("super_admin") ||
    currentUser?.permissions?.includes("*");

  const canManagePassword =
    isSuper ||
    currentUser?.user_type === "admin" ||
    currentUser?.roles?.includes("admin") ||
    currentUser?.permissions?.includes("staff.manage");

  // Password reset & Portal provisioning states
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showResetPass, setShowResetPass] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  const [provisionModalOpen, setProvisionModalOpen] = useState(false);
  const [portalUsername, setPortalUsername] = useState("");
  const [portalPassword, setPortalPassword] = useState("");
  const [confirmPortalPassword, setConfirmPortalPassword] = useState("");
  const [showProvisionPass, setShowProvisionPass] = useState(false);
  const [isProvisioning, setIsProvisioning] = useState(false);

  const {
    data: staff,
    isLoading,
    isError,
    refetch: refetchStaff,
  } = useQuery({
    queryKey: ["staff", id],
    queryFn: () => staffApi.getStaff(id!),
    enabled: Boolean(id),
  });

  const { data: assignmentsData } = useQuery({
    queryKey: ["staff-assignments", id],
    queryFn: () => staffApi.getTeacherAssignments({ teacher: id }),
    enabled: Boolean(id) && activeTab === "assignments",
  });

  const { data: balancesData } = useQuery({
    queryKey: ["staff-leave-balances", id],
    queryFn: () => staffApi.getLeaveBalances({ staff: id }),
    enabled: Boolean(id) && activeTab === "leaves",
  });

  const { data: requestsData } = useQuery({
    queryKey: ["staff-leave-requests", id],
    queryFn: () => staffApi.getLeaveRequests({ staff: id }),
    enabled: Boolean(id) && activeTab === "leaves",
  });

  if (isLoading) {
    return (
      <div className="flex h-72 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-3 border-emerald-700 border-t-transparent" />
          <p className="text-xs text-slate-500 font-medium">
            {t("common.loading", "Loading profile...")}
          </p>
        </div>
      </div>
    );
  }

  if (isError || !staff) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900/50 dark:bg-rose-950/30">
        <p className="text-sm font-semibold text-rose-800 dark:text-rose-300">
          {t("staff.notFound", "Staff record not found or error loading data.")}
        </p>
        <Link to="/staff" className="mt-4 inline-block">
          <Button variant="outline" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            {t("common.back", "Back to Directory")}
          </Button>
        </Link>
      </div>
    );
  }

  const assignments = assignmentsData?.results ?? [];
  const balances = balancesData?.results ?? [];
  const requests = requestsData?.results ?? [];

  const handleDownloadPdf = () => {
    if (staff?.id) {
      window.open(staffApi.getIdCardPdfUrl(staff.id), "_blank");
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      toast.error(t("staff.passwordLengthError", "Password must be at least 6 characters."));
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error(t("validation.passwordMismatch", "Passwords do not match."));
      return;
    }
    setIsResetting(true);
    try {
      const res = await staffApi.resetPassword(staff.id, newPassword);
      toast.success(res.detail || t("staff.passwordResetSuccess", "Password successfully reset."));
      setResetModalOpen(false);
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      toast.error(t("staff.passwordResetError", "Failed to reset password."));
    } finally {
      setIsResetting(false);
    }
  };

  const handleProvisionPortal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (portalPassword.length < 6) {
      toast.error(t("staff.passwordLengthError", "Password must be at least 6 characters."));
      return;
    }
    if (portalPassword !== confirmPortalPassword) {
      toast.error(t("validation.passwordMismatch", "Passwords do not match."));
      return;
    }
    setIsProvisioning(true);
    try {
      await staffApi.createPortalAccount(staff.id, {
        username: portalUsername || undefined,
        password: portalPassword,
      });
      toast.success(t("staff.portalCreatedSuccess", "Portal login account created."));
      setProvisionModalOpen(false);
      setPortalUsername("");
      setPortalPassword("");
      setConfirmPortalPassword("");
      void refetchStaff();
    } catch {
      toast.error(t("staff.portalCreatedError", "Failed to create portal account."));
    } finally {
      setIsProvisioning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <Link to="/staff">
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-lg">
              <ArrowLeft className="h-4 w-4 text-slate-600 dark:text-slate-400" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                {currentLang === "bn" && staff.full_name_bn
                  ? staff.full_name_bn
                  : staff.full_name_en}
              </h1>
              {staff.is_mpo && (
                <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300">
                  MPO
                </span>
              )}
              <span
                className={`rounded-md px-2 py-0.5 text-[11px] font-medium capitalize ${
                  staff.status === "active"
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
                    : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400"
                }`}
              >
                {staff.status}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono">
              ID: {staff.employee_id} • {staff.designation_title || "Staff"} • {staff.department_name || "General"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadPdf}
            className="h-9 gap-2 text-xs border-slate-300 dark:border-slate-700"
          >
            <Download className="h-3.5 w-3.5" />
            <span>{t("staff.downloadCard", "Download ID Card (PDF)")}</span>
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-1">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "overview"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
              : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          <User className="h-4 w-4" />
          {t("staff.tabOverview", "Profile Overview")}
        </button>

        <button
          onClick={() => setActiveTab("assignments")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "assignments"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
              : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          <GraduationCap className="h-4 w-4" />
          {t("staff.tabAssignments", "Teacher Curriculum")}
        </button>

        <button
          onClick={() => setActiveTab("leaves")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "leaves"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
              : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          <Calendar className="h-4 w-4" />
          {t("staff.tabLeaves", "Leaves & Quotas")}
        </button>

        <button
          onClick={() => setActiveTab("idcard")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "idcard"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
              : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          <CreditCard className="h-4 w-4" />
          {t("staff.tabIdCard", "CR80 ID Card")}
        </button>
      </div>

      {/* Tab 1: Profile Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Left Column: Quick Profile & Portal Security */}
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <div className="flex flex-col items-center text-center">
                <div className="h-28 w-24 rounded-lg border-2 border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800 overflow-hidden flex items-center justify-center mb-3">
                  {staff.photo ? (
                    <img
                      src={staff.photo}
                      alt={staff.full_name_en}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <User className="h-12 w-12 text-slate-300 dark:text-slate-600" />
                  )}
                </div>
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {staff.full_name_en}
                </h2>
                {staff.full_name_bn && (
                  <p className="text-xs text-slate-500 font-medium">{staff.full_name_bn}</p>
                )}
                <p className="mt-1 text-xs font-semibold text-emerald-800 dark:text-emerald-400">
                  {staff.designation_title || "Staff Member"}
                </p>
                <p className="text-[11px] text-slate-500">{staff.department_name}</p>
              </div>

              <div className="border-t border-slate-100 pt-3 dark:border-slate-800 space-y-2 text-xs">
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <Phone className="h-3.5 w-3.5 text-slate-400" />
                  <span className="font-mono">{staff.phone}</span>
                </div>
                {staff.email && (
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <Mail className="h-3.5 w-3.5 text-slate-400" />
                    <span className="truncate">{staff.email}</span>
                  </div>
                )}
                {staff.present_address && (
                  <div className="flex items-start gap-2 text-slate-600 dark:text-slate-400">
                    <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0 mt-0.5" />
                    <span className="line-clamp-2">{staff.present_address}</span>
                  </div>
                )}
              </div>

              {/* MPO Information */}
              {staff.is_mpo && (
                <div className="rounded-lg bg-emerald-50/70 p-3 border border-emerald-100 dark:bg-emerald-950/30 dark:border-emerald-900/40 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-emerald-900 dark:text-emerald-300">
                      {t("staff.mpoStatus", "MPO Enrolled")}
                    </span>
                    <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-400">
                    <span>{t("staff.mpoIndex", "Index No")}: </span>
                    <span className="font-mono font-bold text-slate-900 dark:text-slate-200">
                      {staff.mpo_index_number || "—"}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Portal Login & Security Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                    {t("staff.portalAccess", "Portal Access")}
                  </h3>
                </div>
                {staff.user_id ? (
                  <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-[10px] font-bold text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    {t("common.active", "Active")}
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                    {t("staff.noAccess", "No Access")}
                  </span>
                )}
              </div>

              {staff.user_id ? (
                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 block">{t("staff.username", "Username")}</span>
                    <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                      @{staff.username || staff.phone}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">{t("staff.role", "System Role")}</span>
                    <span className="font-medium text-slate-700 dark:text-slate-300 capitalize">
                      {staff.user_type || staff.staff_type}
                    </span>
                  </div>

                  {canManagePassword && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setNewPassword("");
                        setConfirmPassword("");
                        setResetModalOpen(true);
                      }}
                      className="w-full h-8 text-xs font-semibold gap-1.5 mt-2 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
                    >
                      <Lock className="h-3.5 w-3.5 text-slate-600" />
                      <span>{t("staff.resetPassword", "Reset Password")}</span>
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-2 text-xs">
                  <p className="text-[11px] text-slate-500">
                    {t("staff.noPortalHint", "This employee does not have portal login credentials yet.")}
                  </p>
                  {canManagePassword && (
                    <Button
                      size="sm"
                      onClick={() => {
                        setPortalUsername(staff.phone || staff.employee_id || "");
                        setPortalPassword("");
                        setConfirmPortalPassword("");
                        setProvisionModalOpen(true);
                      }}
                      className="w-full h-8 text-xs font-semibold gap-1.5 bg-emerald-800 hover:bg-emerald-900 text-white"
                    >
                      <KeyRound className="h-3.5 w-3.5" />
                      <span>{t("staff.createPortalAccountBtn", "Create Login Access")}</span>
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right Two Columns: Employment & Demographics */}
          <div className="md:col-span-2 space-y-6">
            {/* Employment Details */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
                <Briefcase className="h-4 w-4 text-emerald-700" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  {t("staff.employmentDetails", "Employment & Service Record")}
                </h3>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.employeeId", "Employee ID")}
                  </span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                    {staff.employee_id}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.staffType", "Staff Type")}
                  </span>
                  <span className="font-medium text-slate-900 dark:text-slate-100 capitalize">
                    {staff.staff_type}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.joiningDate", "Date of Joining")}
                  </span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">
                    {staff.joining_date}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.confirmationDate", "Confirmation Date")}
                  </span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">
                    {staff.confirmation_date || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.tinNumber", "TIN Number")}
                  </span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">
                    {staff.tin_number || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.nid", "National ID (NID)")}
                  </span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">
                    {staff.nid ? `••••••••${staff.nid.slice(-4)}` : "—"}
                  </span>
                </div>
              </div>
            </div>

            {/* Demographics & Personal */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
                <User className="h-4 w-4 text-emerald-700" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  {t("staff.personalDetails", "Personal & Demographic Profile")}
                </h3>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.gender", "Gender")}
                  </span>
                  <span className="font-medium capitalize text-slate-900 dark:text-slate-100">
                    {staff.gender}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.bloodGroup", "Blood Group")}
                  </span>
                  <span className="font-bold text-rose-700 dark:text-rose-400">
                    {staff.blood_group || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.dob", "Date of Birth")}
                  </span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">
                    {staff.dob || "—"}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2">
                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.presentAddress", "Present Address")}
                  </span>
                  <p className="text-slate-700 dark:text-slate-300 mt-0.5">
                    {staff.present_address || "—"}
                  </p>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.permanentAddress", "Permanent Address")}
                  </span>
                  <p className="text-slate-700 dark:text-slate-300 mt-0.5">
                    {staff.permanent_address || "—"}
                  </p>
                </div>
              </div>
            </div>

            {/* Emergency Contacts */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-3">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-2 dark:border-slate-800">
                <Shield className="h-4 w-4 text-emerald-700" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  {t("staff.emergencyContact", "Emergency Contact")}
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.contactName", "Contact Name")}
                  </span>
                  <span className="font-medium text-slate-900 dark:text-slate-100">
                    {staff.emergency_contact_name || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.contactRelation", "Relationship")}
                  </span>
                  <span className="text-slate-900 dark:text-slate-100 capitalize">
                    {staff.emergency_contact_relation || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block text-[11px]">
                    {t("staff.contactPhone", "Emergency Phone")}
                  </span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">
                    {staff.emergency_contact_phone || "—"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Curriculum Assignments */}
      {activeTab === "assignments" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {t("staff.assignedSubjects", "Teacher Course & Class Assignments")}
              </h3>
              <p className="text-xs text-slate-500">
                {t("staff.assignedSubjectsDesc", "Curriculum teaching load across academic sections.")}
              </p>
            </div>
          </div>

          {assignments.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              {t("staff.noAssignments", "No teaching subjects currently assigned to this staff member.")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("academic.subject", "Subject")}</th>
                    <th className="px-4 py-3 font-semibold">{t("academic.class", "Class")}</th>
                    <th className="px-4 py-3 font-semibold">{t("academic.section", "Section")}</th>
                    <th className="px-4 py-3 font-semibold">{t("academic.session", "Academic Session")}</th>
                    <th className="px-4 py-3 font-semibold text-center">{t("staff.periodsPerWeek", "Periods/Wk")}</th>
                    <th className="px-4 py-3 font-semibold text-center">{t("staff.primaryTeacher", "Primary")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {assignments.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        {item.subject_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {item.class_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300 font-mono">
                        {item.section_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {item.session_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-center font-mono font-semibold">
                        {item.periods_per_week ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {item.is_primary_teacher ? (
                          <span className="inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300">
                            Yes
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[11px]">No</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Leaves & Balances */}
      {activeTab === "leaves" && (
        <div className="space-y-6">
          {/* Leave Quota Cards */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-3">
              {t("staff.leaveBalances", "Annual Leave Allocations & Balances")}
            </h3>
            {balances.length === 0 ? (
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
                {t("staff.noBalances", "No leave quotas initialized for this staff member.")}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                {balances.map((b) => (
                  <div
                    key={b.id}
                    className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                        {b.leave_type_name || b.leave_type_code}
                      </span>
                      <span className="text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-600 dark:text-slate-300">
                        {b.leave_type_code}
                      </span>
                    </div>
                    <div className="flex items-baseline justify-between pt-1">
                      <div>
                        <span className="text-2xl font-extrabold text-emerald-800 dark:text-emerald-400 font-mono">
                          {b.remaining_days}
                        </span>
                        <span className="text-[11px] text-slate-500 ml-1">
                          {t("staff.daysLeft", "left")}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {b.used_days} / {b.allocated_days} {t("staff.used", "used")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Leave Request History */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {t("staff.leaveHistory", "Leave Application History")}
              </h3>
            </div>

            {requests.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                {t("staff.noLeaveHistory", "No leave applications recorded for this staff member.")}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="px-4 py-3 font-semibold">{t("staff.leaveType", "Type")}</th>
                      <th className="px-4 py-3 font-semibold">{t("staff.dates", "Duration")}</th>
                      <th className="px-4 py-3 font-semibold text-center">{t("staff.days", "Days")}</th>
                      <th className="px-4 py-3 font-semibold">{t("staff.reason", "Reason")}</th>
                      <th className="px-4 py-3 font-semibold">{t("staff.status", "Status")}</th>
                      <th className="px-4 py-3 font-semibold">{t("staff.approver", "Approved By")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {requests.map((req) => (
                      <tr key={req.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                          {req.leave_type_code}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                          {req.start_date} to {req.end_date}
                        </td>
                        <td className="px-4 py-3 text-center font-mono font-bold">
                          {req.days_count}
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-[200px] truncate">
                          {req.reason}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                              req.status === "approved"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                                : req.status === "rejected"
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300"
                                : "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300"
                            }`}
                          >
                            {req.status === "approved" && <CheckCircle2 className="h-3 w-3" />}
                            {req.status === "rejected" && <XCircle className="h-3 w-3" />}
                            {req.status === "pending" && <Clock className="h-3 w-3" />}
                            {req.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-500">
                          {req.approver_name || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: ID Card Preview */}
      {activeTab === "idcard" && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-xs dark:border-slate-800 dark:bg-slate-900 flex flex-col items-center">
          <StaffIDCardPreview staff={staff} onDownloadPdf={handleDownloadPdf} />
        </div>
      )}

      {/* Dialog: Reset Password */}
      <Dialog open={resetModalOpen} onOpenChange={setResetModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-sm font-bold">
              <Lock className="h-4 w-4 text-emerald-800" />
              <span>{t("staff.resetPasswordTitle", "Reset Portal Password")}</span>
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { void handleResetPassword(e); }} className="space-y-4 pt-2">
            <p className="text-xs text-slate-500">
              {t(
                "staff.resetPasswordHint",
                "Set a new dashboard login password for this employee. They can use this to sign in immediately."
              )}
            </p>

            <FormField>
              <FormLabel required className="text-xs font-medium">
                {t("staff.newPassword", "New Password")}
              </FormLabel>
              <div className="relative">
                <Input
                  type={showResetPass ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min. 6 characters"
                  className="h-9 text-xs rounded-lg pr-8 font-mono"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowResetPass(!showResetPass)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  aria-label={showResetPass ? "Hide password" : "Show password"}
                >
                  {showResetPass ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              </div>
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium">
                {t("staff.confirmPassword", "Confirm Password")}
              </FormLabel>
              <Input
                type={showResetPass ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat new password"
                className="h-9 text-xs rounded-lg font-mono"
                required
              />
            </FormField>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setResetModalOpen(false)}
                className="text-xs"
              >
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isResetting}
                className="text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {isResetting
                  ? t("common.saving", "Saving...")
                  : t("staff.saveNewPassword", "Update Password")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialog: Provision Portal Account */}
      <Dialog open={provisionModalOpen} onOpenChange={setProvisionModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-sm font-bold">
              <KeyRound className="h-4 w-4 text-emerald-800" />
              <span>{t("staff.provisionPortalTitle", "Create Portal Login Access")}</span>
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { void handleProvisionPortal(e); }} className="space-y-4 pt-2">
            <p className="text-xs text-slate-500">
              {t(
                "staff.provisionPortalHint",
                "Create a user account so this employee can log into the school management portal."
              )}
            </p>

            <FormField>
              <FormLabel className="text-xs font-medium">
                {t("staff.portalUsername", "Portal Username")}
              </FormLabel>
              <Input
                value={portalUsername}
                onChange={(e) => setPortalUsername(e.target.value)}
                placeholder={staff.phone || "e.g. username"}
                className="h-9 text-xs rounded-lg font-mono"
              />
              <p className="text-[10px] text-slate-400 mt-1">
                {t("staff.usernameHint", "Defaults to Employee ID or Phone if blank")}
              </p>
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium">
                {t("staff.initialPassword", "Initial Password")}
              </FormLabel>
              <div className="relative">
                <Input
                  type={showProvisionPass ? "text" : "password"}
                  value={portalPassword}
                  onChange={(e) => setPortalPassword(e.target.value)}
                  placeholder="Min. 6 characters"
                  className="h-9 text-xs rounded-lg pr-8 font-mono"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowProvisionPass(!showProvisionPass)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  aria-label={showProvisionPass ? "Hide password" : "Show password"}
                >
                  {showProvisionPass ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              </div>
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium">
                {t("staff.confirmPassword", "Confirm Password")}
              </FormLabel>
              <Input
                type={showProvisionPass ? "text" : "password"}
                value={confirmPortalPassword}
                onChange={(e) => setConfirmPortalPassword(e.target.value)}
                placeholder="Repeat password"
                className="h-9 text-xs rounded-lg font-mono"
                required
              />
            </FormField>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setProvisionModalOpen(false)}
                className="text-xs"
              >
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isProvisioning}
                className="text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {isProvisioning
                  ? t("common.creating", "Creating...")
                  : t("staff.createAccount", "Create Account")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
