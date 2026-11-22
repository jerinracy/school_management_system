import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Briefcase,
  CheckCircle2,
  CreditCard,
  Edit2,
  Eye,
  EyeOff,
  History,
  KeyRound,
  Mail,
  MapPin,
  Phone,
  Plus,
  Search,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Trash2,
  User,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { studentsApi } from "@/features/students/api/studentsApi";
import { academicApi } from "@/features/academics/api/academicApi";
import { institutionApi } from "@/features/institutions/api/institutionApi";
import { StudentIDCardPreview } from "@/features/students/components/StudentIDCardPreview";
import { EditStudentDialog } from "@/features/students/components/EditStudentDialog";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { Can } from "@/features/auth/permissions";
import { cn } from "@/lib/utils";
import type { components } from "@/types/api";

export function StudentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("profile");

  // New Enrollment Dialog State
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [enrollSessionId, setEnrollSessionId] = useState("");
  const [enrollClassId, setEnrollClassId] = useState("");
  const [enrollSectionId, setEnrollSectionId] = useState("");
  const [enrollRollNo, setEnrollRollNo] = useState<number>(1);
  const [enrollError, setEnrollError] = useState<string | null>(null);

  // Mobile App Login Modal State
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [loginPhone, setLoginPhone] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginModalError, setLoginModalError] = useState<string | null>(null);

  const assignLoginMutation = useMutation({
    mutationFn: () => {
      if (!id) throw new Error("Student ID missing");
      if (!loginPassword || loginPassword.length < 6) {
        throw new Error("Password must be at least 6 characters.");
      }
      return studentsApi.assignStudentLogin(id, {
        phone: loginPhone || undefined,
        password: loginPassword,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["student", id] });
      setIsLoginModalOpen(false);
      setLoginPassword("");
      setLoginModalError(null);
    },
    onError: (err: unknown) => {
      setLoginModalError((err as Error).message || "Failed to set login credentials.");
    },
  });

  // Edit & Delete modal states
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!id) throw new Error("Student ID missing");
      return studentsApi.deleteStudent(id);
    },
    onSuccess: () => {
      toast.success(t("students.deleteSuccess", "Student profile deleted successfully."));
      void queryClient.invalidateQueries({ queryKey: ["students"] });
      void navigate("/students");
    },
    onError: (err: unknown) => {
      toast.error((err as Error).message || "Failed to delete student.");
    },
  });

  const handleGenerateStudentPassword = () => {
    const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%";
    let pass = "";
    for (let i = 0; i < 8; i++) {
      pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setLoginPassword(pass);
  };

  // Student Query
  const {
    data: student,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["student", id],
    queryFn: () => studentsApi.getStudent(id!),
    enabled: Boolean(id),
  });

  // Supporting Options Queries
  const { data: sessions = [] } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => institutionApi.getSessions(),
    enabled: isEnrollModalOpen,
  });

  const { data: classes = [] } = useQuery({
    queryKey: ["classes"],
    queryFn: () => academicApi.getClasses(),
    enabled: isEnrollModalOpen,
  });

  const { data: sections = [] } = useQuery({
    queryKey: ["sections", enrollClassId],
    queryFn: () => academicApi.getSections(enrollClassId),
    enabled: Boolean(enrollClassId),
  });

  // Enrollment Mutation
  const enrollMutation = useMutation({
    mutationFn: () =>
      studentsApi.createEnrollment({
        student: id!,
        session: enrollSessionId,
        class_level: enrollClassId,
        section: enrollSectionId,
        roll_no: Number(enrollRollNo),
        status: "active",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["student", id] });
      setIsEnrollModalOpen(false);
      setEnrollError(null);
    },
    onError: (err: unknown) => {
      setEnrollError((err as Error).message || "Failed to enroll student.");
    },
  });

  // Link Guardian Modal State
  const [isLinkGuardianModalOpen, setIsLinkGuardianModalOpen] = useState(false);
  const [guardianSearch, setGuardianSearch] = useState("");
  const [selectedGuardianId, setSelectedGuardianId] = useState("");
  const [selectedRelation, setSelectedRelation] = useState<
    components["schemas"]["RelationEnum"]
  >("father");
  const [isPrimaryGuardian, setIsPrimaryGuardian] = useState(false);
  const [canPickup, setCanPickup] = useState(true);
  const [receivesSms, setReceivesSms] = useState(true);
  const [financialResponsible, setFinancialResponsible] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  // Unlink Dialog State
  const [unlinkingGuardian, setUnlinkingGuardian] = useState<{
    id: string;
    name: string;
  } | null>(null);

  // Guardian Search Query
  const { data: searchGuardiansData, isFetching: isSearchingGuardians } = useQuery({
    queryKey: ["guardiansSearch", guardianSearch],
    queryFn: () => studentsApi.getGuardians({ search: guardianSearch, page: 1 }),
    enabled: isLinkGuardianModalOpen && guardianSearch.trim().length >= 2,
  });

  const searchedGuardians = searchGuardiansData?.results ?? [];

  // Link Guardian Mutation
  const linkGuardianMutation = useMutation({
    mutationFn: () => {
      if (!selectedGuardianId || !id) {
        throw new Error("Please select a guardian");
      }
      return studentsApi.linkGuardian(selectedGuardianId, {
        student_id: id,
        relation: selectedRelation,
        is_primary: isPrimaryGuardian,
        can_pickup: canPickup,
        receives_sms: receivesSms,
        financial_responsible: financialResponsible,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["student", id] });
      setIsLinkGuardianModalOpen(false);
      setSelectedGuardianId("");
      setGuardianSearch("");
      setLinkError(null);
    },
    onError: (err: unknown) => {
      setLinkError((err as Error).message || "Failed to link guardian.");
    },
  });

  // Unlink Guardian Mutation
  const unlinkGuardianMutation = useMutation({
    mutationFn: (guardianId: string) => studentsApi.unlinkGuardian(guardianId, id!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["student", id] });
      setUnlinkingGuardian(null);
    },
  });

  if (isLoading) {
    return (
      <div className="py-24 text-center">
        <div className="inline-flex items-center gap-2 text-xs text-slate-500">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
          <span>{t("common.loading", "Loading student profile...")}</span>
        </div>
      </div>
    );
  }

  if (isError || !student) {
    return (
      <div className="py-20 text-center space-y-3">
        <p className="text-sm font-semibold text-danger">
          {t("students.notFound", "Student profile not found.")}
        </p>
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void refetch();
            }}
            className="text-xs"
          >
            {t("common.retry", "Retry")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void navigate("/students");
            }}
            className="text-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1" />
            <span>{t("students.backToDirectory", "Back to Student Directory")}</span>
          </Button>
        </div>
      </div>
    );
  }

  const activeEnrollment = student.enrollments?.[0];

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Return Nav */}
      <div className="flex items-center justify-between">
        <Link
          to="/students"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{t("students.backToDirectory", "Back to Student Directory")}</span>
        </Link>
      </div>

      {/* Student Identity Header Card */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5">
          <div className="flex items-center gap-4">
            {/* Student Avatar / Initials */}
            <div className="h-16 w-16 shrink-0 rounded-2xl bg-emerald-100/80 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-800 dark:text-emerald-300 font-extrabold text-xl shadow-2xs">
              {student.photo ? (
                <img
                  src={student.photo}
                  alt={student.name_en}
                  className="h-full w-full object-cover rounded-2xl"
                />
              ) : (
                student.name_en.slice(0, 2).toUpperCase()
              )}
            </div>

            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                  {currentLang === "bn" && student.name_bn ? student.name_bn : student.name_en}
                </h1>
                <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
                  {(student.status ?? "active").toUpperCase()}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                <span className="font-mono font-medium text-slate-700 dark:text-slate-300">
                  ID: {student.student_id}
                </span>
                {activeEnrollment && (
                  <>
                    <span>•</span>
                    <span className="font-semibold text-emerald-800 dark:text-emerald-400">
                      {activeEnrollment.class_name} • {activeEnrollment.section_name} (Roll {activeEnrollment.roll_no})
                    </span>
                    <span>•</span>
                    <span>{activeEnrollment.session_name}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            <Can perm="students.manage">
              <Button
                variant={student.has_app_account ? "outline" : "default"}
                size="sm"
                onClick={() => {
                  setLoginPhone(student.login_phone || student.phone || student.emergency_contact_phone || "");
                  setLoginPassword("");
                  setLoginModalError(null);
                  setIsLoginModalOpen(true);
                }}
                className={cn(
                  "gap-1.5 text-xs rounded-lg font-semibold",
                  !student.has_app_account && "bg-amber-800 hover:bg-amber-900 text-white"
                )}
              >
                <Smartphone className="h-3.5 w-3.5" />
                <span>
                  {student.has_app_account
                    ? t("students.resetAppPassword", "Reset Password")
                    : t("students.setupAppLogin", "Setup App Login")}
                </span>
              </Button>
            </Can>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveTab("id-card")}
              className="gap-1.5 text-xs rounded-lg"
            >
              <CreditCard className="h-3.5 w-3.5" />
              <span>{t("students.viewIdCard", "View ID Card")}</span>
            </Button>

            <Can perm="students.manage">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditModalOpen(true)}
                className="gap-1.5 text-xs rounded-lg"
              >
                <Edit2 className="h-3.5 w-3.5" />
                <span>{t("common.edit", "Edit")}</span>
              </Button>
            </Can>

            <Can perm="students.manage">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteDialogOpen(true)}
                className="gap-1.5 text-xs rounded-lg text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-rose-200 dark:border-rose-900/50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>{t("common.delete", "Delete")}</span>
              </Button>
            </Can>

            <Can perm="students.manage">
              <Button
                size="sm"
                onClick={() => setIsEnrollModalOpen(true)}
                className="gap-1.5 text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>{t("students.enrollClass", "New Enrollment")}</span>
              </Button>
            </Can>
          </div>
        </div>
      </div>

      {/* Detail Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="mb-6 grid w-full max-w-md grid-cols-3 rounded-xl bg-slate-100/90 dark:bg-slate-800/60 p-1 border border-slate-200/60">
          <TabsTrigger
            value="profile"
            className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-slate-900 data-[state=active]:shadow-2xs text-slate-600 dark:text-slate-400"
          >
            <User className="h-3.5 w-3.5" />
            <span>{t("students.tabProfile", "Profile")}</span>
          </TabsTrigger>
          <TabsTrigger
            value="enrollments"
            className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-slate-900 data-[state=active]:shadow-2xs text-slate-600 dark:text-slate-400"
          >
            <History className="h-3.5 w-3.5" />
            <span>{t("students.tabEnrollments", "Enrollments")}</span>
          </TabsTrigger>
          <TabsTrigger
            value="id-card"
            className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-slate-900 data-[state=active]:shadow-2xs text-slate-600 dark:text-slate-400"
          >
            <CreditCard className="h-3.5 w-3.5" />
            <span>{t("students.tabIdCard", "ID Card")}</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Profile Details */}
        <TabsContent value="profile" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Demographic Information */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-2xs space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 pb-2">
                {t("students.personalDetails", "Demographic Details")}
              </h3>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block">{t("students.nameEn", "Full Name (English)")}</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-100">{student.name_en}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">{t("students.nameBn", "Full Name (Bangla)")}</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-100">{student.name_bn || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">{t("students.dob", "Date of Birth")}</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-100">{student.dob}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">{t("students.gender", "Gender")}</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-100 capitalize">{student.gender}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">{t("students.bloodGroup", "Blood Group")}</span>
                  <span className="font-semibold text-rose-600 dark:text-rose-400">{student.blood_group || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">{t("students.religion", "Religion")}</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-100 capitalize">{student.religion || "—"}</span>
                </div>
              </div>
            </div>

            {/* Official Identification & Emergency Contacts */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-2xs space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 pb-2">
                {t("students.officialGovtId", "Government Identification & Contacts")}
              </h3>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-400 block">{t("students.birthRegNo", "Birth Registration No (17 Digits)")}</span>
                  <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                    {student.birth_reg_no || t("common.notProvided", "Not Provided")}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-slate-400 block">{t("students.emergencyContactName", "Emergency Contact")}</span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {student.emergency_contact_name || "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">{t("students.emergencyContactPhone", "Emergency Phone")}</span>
                    <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                      {student.emergency_contact_phone || "—"}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block">{t("students.presentAddress", "Present Address")}</span>
                  <span className="text-slate-700 dark:text-slate-300">{student.present_address}</span>
                </div>
              </div>
            </div>

            {/* Mobile App Login Credentials */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-2xs space-y-4 md:col-span-2">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="h-8 w-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-800 dark:text-emerald-300">
                    <Smartphone className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                      {t("students.appLoginTitle", "Mobile App & Portal Login Account")}
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      {t(
                        "students.appLoginExplainer",
                        "The student logs into the mobile app using their phone number and password."
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-bold border",
                      student.has_app_account
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800"
                        : "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800"
                    )}
                  >
                    {student.has_app_account
                      ? t("students.appLoginActive", "Active Login")
                      : t("students.appLoginNotConfigured", "No Login Account")}
                  </span>

                  <Can perm="students.manage">
                    <Button
                      size="sm"
                      variant={student.has_app_account ? "outline" : "default"}
                      onClick={() => {
                        setLoginPhone(student.login_phone || student.phone || student.emergency_contact_phone || "");
                        setLoginPassword("");
                        setLoginModalError(null);
                        setIsLoginModalOpen(true);
                      }}
                      className={cn(
                        "text-xs font-semibold gap-1.5 rounded-lg",
                        !student.has_app_account && "bg-emerald-800 hover:bg-emerald-900 text-white"
                      )}
                    >
                      <KeyRound className="h-3.5 w-3.5" />
                      <span>
                        {student.has_app_account
                          ? t("students.resetPasswordBtn", "Reset Password")
                          : t("students.setupLoginBtn", "Create Login Details")}
                      </span>
                    </Button>
                  </Can>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block">{t("students.loginPhone", "Login Mobile Number")}</span>
                  <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-sm">
                    {student.login_phone || student.phone || t("common.notConfigured", "No phone assigned")}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">{t("students.passwordPolicy", "Password Policy")}</span>
                  <span className="text-slate-600 dark:text-slate-400">
                    {t(
                      "students.passwordPolicyInfo",
                      "Students can keep the initial password or change it in the mobile app settings."
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Guardians & Household Contacts Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-2xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                    <Users className="h-4 w-4 text-emerald-600" />
                    <span>{t("students.guardiansContacts", "Guardians & Family Contacts")}</span>
                  </h3>
                  <span className="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-bold text-slate-600 dark:text-slate-300">
                    {student.guardians?.length ?? 0}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {t("students.guardiansContactsSubtitle", "Verified parents, legal guardians, and authorized pickup contacts.")}
                </p>
              </div>

              <Can perm="students.manage">
                <Button
                  size="sm"
                  onClick={() => {
                    setSelectedGuardianId("");
                    setGuardianSearch("");
                    setSelectedRelation("father");
                    setIsPrimaryGuardian((student.guardians?.length ?? 0) === 0);
                    setCanPickup(true);
                    setReceivesSms(true);
                    setFinancialResponsible((student.guardians?.length ?? 0) === 0);
                    setLinkError(null);
                    setIsLinkGuardianModalOpen(true);
                  }}
                  className="gap-1.5 text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg shadow-xs"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>{t("students.linkGuardian", "Link Guardian")}</span>
                </Button>
              </Can>
            </div>

            {!student.guardians || student.guardians.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 dark:border-slate-800 p-8 text-center text-slate-400">
                <Users className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                  {t("students.noGuardiansLinked", "No guardians linked to this student yet.")}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {student.guardians.map((g) => (
                  <div
                    key={g.id}
                    className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 p-4 space-y-3 relative hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
                  >
                    {/* Guardian Name & Badges */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-sm text-slate-900 dark:text-slate-100">
                            {currentLang === "bn" && g.name_bn ? g.name_bn : g.name_en}
                          </span>
                          {g.is_primary && (
                            <Badge variant="primary" className="text-[10px]">
                              {t("students.primaryBadge", "Primary")}
                            </Badge>
                          )}
                          <Badge variant="neutral" className="text-[10px] capitalize">
                            {g.relation}
                          </Badge>
                        </div>

                        {/* Mobile Phone */}
                        <div className="flex items-center gap-2 text-xs font-mono font-medium text-slate-700 dark:text-slate-300">
                          <Phone className="h-3.5 w-3.5 text-emerald-600" />
                          <a href={`tel:${g.phone}`} className="hover:underline text-emerald-700 dark:text-emerald-400">
                            {g.phone}
                          </a>
                          {g.alt_phone && (
                            <span className="text-slate-400 text-[11px]">/ {g.alt_phone}</span>
                          )}
                        </div>
                      </div>

                      {/* Unlink Action */}
                      <Can perm="students.manage">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setUnlinkingGuardian({ id: g.guardian_id, name: g.name_en })}
                          className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 rounded-lg"
                          title={t("students.unlinkGuardian", "Unlink")}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </Can>
                    </div>

                    {/* Additional details */}
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1 border-t border-slate-100 dark:border-slate-800">
                      {g.occupation && (
                        <div className="flex items-center gap-1.5">
                          <Briefcase className="h-3 w-3 text-slate-400" />
                          <span className="truncate">{g.occupation}</span>
                        </div>
                      )}
                      {g.nid && (
                        <div className="font-mono text-slate-600 dark:text-slate-400 truncate">
                          NID: {g.nid}
                        </div>
                      )}
                      {g.email && (
                        <div className="flex items-center gap-1.5 col-span-2 truncate">
                          <Mail className="h-3 w-3 text-slate-400" />
                          <span className="truncate">{g.email}</span>
                        </div>
                      )}
                      {g.present_address && (
                        <div className="flex items-center gap-1.5 col-span-2 text-slate-600 dark:text-slate-400 truncate">
                          <MapPin className="h-3 w-3 text-slate-400 shrink-0" />
                          <span className="truncate">{g.present_address}</span>
                        </div>
                      )}
                    </div>

                    {/* Permission Flags */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {g.can_pickup && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/60 px-2 py-0.5 rounded-md">
                          <CheckCircle2 className="h-3 w-3" />
                          <span>{t("students.canPickup", "Pickup Authorized")}</span>
                        </span>
                      )}
                      {g.receives_sms && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-blue-700 bg-blue-50 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/60 px-2 py-0.5 rounded-md">
                          <CheckCircle2 className="h-3 w-3" />
                          <span>{t("students.receivesSms", "Receives SMS")}</span>
                        </span>
                      )}
                      {g.financial_responsible && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/60 px-2 py-0.5 rounded-md">
                          <ShieldCheck className="h-3 w-3" />
                          <span>{t("students.financialResponsible", "Financial Contact")}</span>
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 2: Historical Enrollments */}
        <TabsContent value="enrollments" className="space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3">{t("institutions.session", "Academic Session")}</th>
                  <th className="px-4 py-3">{t("academics.class", "Class & Section")}</th>
                  <th className="px-4 py-3">{t("students.roll", "Roll No")}</th>
                  <th className="px-4 py-3">{t("students.enrollmentDate", "Enrolled Date")}</th>
                  <th className="px-4 py-3">{t("common.status", "Status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {!student.enrollments || student.enrollments.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      {t("students.noEnrollments", "No enrollment records on file.")}
                    </td>
                  </tr>
                ) : (
                  student.enrollments.map((enr) => (
                    <tr key={enr.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        {enr.session_name}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {enr.class_name} • {enr.section_name}
                      </td>
                      <td className="px-4 py-3 font-mono font-bold text-emerald-800 dark:text-emerald-400">
                        {enr.roll_no}
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-mono">
                        {enr.enrollment_date}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
                          {(enr.status ?? "active").toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* Tab 3: Official ID Card */}
        <TabsContent value="id-card" className="space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 shadow-2xs flex justify-center">
            <StudentIDCardPreview
              student={student}
              onDownloadPdf={() => window.open(studentsApi.getIdCardPdfUrl(student.id), "_blank")}
            />
          </div>
        </TabsContent>
      </Tabs>

      {/* New Enrollment Modal */}
      <Dialog open={isEnrollModalOpen} onOpenChange={setIsEnrollModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100">
              {t("students.enrollStudent", "Enroll Student")}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              {t("students.enrollDescription", "Assign student to an active academic session, class grade, and section.")}
            </DialogDescription>
          </DialogHeader>

          {enrollError && (
            <div className="rounded-lg border border-danger/20 bg-danger/10 p-2.5 text-xs text-danger font-medium">
              {enrollError}
            </div>
          )}

          <div className="space-y-3.5 py-2">
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("institutions.session", "Academic Session")}
              </FormLabel>
              <Select value={enrollSessionId} onValueChange={setEnrollSessionId}>
                <SelectTrigger className="h-9 text-xs rounded-lg">
                  <SelectValue placeholder={t("institutions.selectSession", "Select Session")} />
                </SelectTrigger>
                <SelectContent>
                  {sessions.map((s) => (
                    <SelectItem key={s.id} value={s.id} className="text-xs">
                      {s.name} {s.is_current ? `(${t("common.current", "Current")})` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("academics.class", "Class Grade")}
              </FormLabel>
              <Select value={enrollClassId} onValueChange={(val) => { setEnrollClassId(val); setEnrollSectionId(""); }}>
                <SelectTrigger className="h-9 text-xs rounded-lg">
                  <SelectValue placeholder={t("academics.selectClass", "Select Class")} />
                </SelectTrigger>
                <SelectContent>
                  {classes.map((c) => (
                    <SelectItem key={c.id} value={c.id} className="text-xs">
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("academics.section", "Section")}
              </FormLabel>
              <Select value={enrollSectionId} onValueChange={setEnrollSectionId} disabled={!enrollClassId}>
                <SelectTrigger className="h-9 text-xs rounded-lg">
                  <SelectValue placeholder={t("academics.selectSection", "Select Section")} />
                </SelectTrigger>
                <SelectContent>
                  {sections.map((sec) => (
                    <SelectItem key={sec.id} value={sec.id} className="text-xs">
                      {sec.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.rollNo", "Class Roll Number")}
              </FormLabel>
              <Input
                type="number"
                min={1}
                value={enrollRollNo}
                onChange={(e) => setEnrollRollNo(Number(e.target.value))}
                className="h-9 text-xs rounded-lg"
              />
            </FormField>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEnrollModalOpen(false)}
              className="text-xs rounded-lg"
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              size="sm"
              onClick={() => enrollMutation.mutate()}
              disabled={enrollMutation.isPending || !enrollSessionId || !enrollClassId || !enrollSectionId}
              className="text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
            >
              {enrollMutation.isPending ? t("common.saving", "Enrolling...") : t("students.confirmEnroll", "Enroll Student")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Link Guardian Dialog */}
      <Dialog open={isLinkGuardianModalOpen} onOpenChange={setIsLinkGuardianModalOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100">
              {t("students.linkGuardian", "Link Guardian to Student")}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              {t("students.linkGuardianSubtitle", "Search an existing guardian to link or configure authorization permissions.")}
            </DialogDescription>
          </DialogHeader>

          {linkError && (
            <div className="rounded-lg border border-danger/20 bg-danger/10 p-2.5 text-xs text-danger font-medium">
              {linkError}
            </div>
          )}

          <div className="space-y-4 py-2">
            {/* Guardian Search */}
            <div className="space-y-1.5">
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.guardian", "Guardian Record")}
              </FormLabel>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                <Input
                  value={guardianSearch}
                  onChange={(e) => setGuardianSearch(e.target.value)}
                  placeholder={t("students.searchGuardiansToLink", "Search existing guardian by name or phone...")}
                  className="h-9 pl-9 text-xs rounded-lg"
                />
                {isSearchingGuardians && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-400">
                    {t("common.searching", "Searching...")}
                  </span>
                )}
              </div>

              {/* Autocomplete Results */}
              {guardianSearch.trim().length >= 2 && searchedGuardians.length > 0 && (
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-1.5 max-h-40 overflow-y-auto space-y-1">
                  {searchedGuardians.map((g) => {
                    const isSelected = selectedGuardianId === g.id;
                    const isAlreadyLinked = student?.guardians?.some((item) => item.guardian_id === g.id);
                    return (
                      <div
                        key={g.id}
                        className={`flex items-center justify-between px-2.5 py-1.5 rounded-md transition-colors text-xs ${
                          isSelected ? "bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800" : "hover:bg-white dark:hover:bg-slate-800"
                        }`}
                      >
                        <div>
                          <div className="font-semibold text-slate-800 dark:text-slate-200">
                            {currentLang === "bn" && g.name_bn ? g.name_bn : g.name_en}
                          </div>
                          <div className="text-[11px] font-mono text-slate-500">
                            {g.phone} {g.occupation ? `• ${g.occupation}` : ""}
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant={isSelected ? "default" : "outline"}
                          disabled={Boolean(isAlreadyLinked)}
                          onClick={() => {
                            setSelectedGuardianId(g.id);
                            if (g.relation_default) {
                              setSelectedRelation(g.relation_default);
                            }
                          }}
                          className="h-6 px-2 text-[11px]"
                        >
                          {isAlreadyLinked ? t("common.linked", "Linked") : isSelected ? t("common.selected", "Selected") : t("common.select", "Select")}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Relationship Dropdown */}
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.relation", "Relationship to Student")}
              </FormLabel>
              <Select
                value={selectedRelation}
                onValueChange={(val) => setSelectedRelation(val as never)}
              >
                <SelectTrigger className="h-9 text-xs rounded-lg">
                  <SelectValue placeholder={t("students.selectRelation", "Select Relation")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="father">{t("students.relFather", "Father")}</SelectItem>
                  <SelectItem value="mother">{t("students.relMother", "Mother")}</SelectItem>
                  <SelectItem value="legal_guardian">{t("students.relLegalGuardian", "Legal Guardian")}</SelectItem>
                  <SelectItem value="grandparent">{t("students.relGrandparent", "Grandparent")}</SelectItem>
                  <SelectItem value="uncle">{t("students.relUncle", "Uncle")}</SelectItem>
                  <SelectItem value="aunt">{t("students.relAunt", "Aunt")}</SelectItem>
                  <SelectItem value="brother">{t("students.relBrother", "Brother")}</SelectItem>
                  <SelectItem value="sister">{t("students.relSister", "Sister")}</SelectItem>
                  <SelectItem value="other">{t("students.relOther", "Other")}</SelectItem>
                </SelectContent>
              </Select>
            </FormField>

            {/* Permission Flags */}
            <div className="rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 p-3 space-y-2.5">
              <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block">
                {t("students.authorizationPermissions", "Authorization & Permissions")}
              </span>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={isPrimaryGuardian}
                    onChange={(e) => setIsPrimaryGuardian(e.target.checked)}
                    className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                  />
                  <span>{t("students.isPrimary", "Primary Contact")}</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={canPickup}
                    onChange={(e) => setCanPickup(e.target.checked)}
                    className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                  />
                  <span>{t("students.canPickup", "Authorized Pickup")}</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={receivesSms}
                    onChange={(e) => setReceivesSms(e.target.checked)}
                    className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                  />
                  <span>{t("students.receivesSms", "Receives SMS")}</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={financialResponsible}
                    onChange={(e) => setFinancialResponsible(e.target.checked)}
                    className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                  />
                  <span>{t("students.financialResponsible", "Financial Contact")}</span>
                </label>
              </div>
            </div>

            <div className="text-right">
              <Link
                to="/students/guardians"
                className="text-[11px] text-emerald-700 dark:text-emerald-400 hover:underline font-medium"
              >
                + {t("students.newGuardianRecord", "Need to create a new guardian record first?")}
              </Link>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLinkGuardianModalOpen(false)}
              className="text-xs rounded-lg"
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              size="sm"
              onClick={() => linkGuardianMutation.mutate()}
              disabled={linkGuardianMutation.isPending || !selectedGuardianId}
              className="text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
            >
              {linkGuardianMutation.isPending
                ? t("common.saving", "Linking...")
                : t("students.linkGuardian", "Link Guardian")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unlink Confirmation Dialog */}
      <Dialog
        open={Boolean(unlinkingGuardian)}
        onOpenChange={(open) => !open && setUnlinkingGuardian(null)}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100">
              {t("students.unlinkGuardian", "Unlink Guardian")}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              {t(
                "students.unlinkGuardianConfirm",
                "Are you sure you want to unlink this guardian from the student?",
              )}
            </DialogDescription>
          </DialogHeader>

          {unlinkingGuardian && (
            <div className="py-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
              {unlinkingGuardian.name}
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setUnlinkingGuardian(null)}
              className="text-xs rounded-lg"
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              size="sm"
              onClick={() => {
                if (unlinkingGuardian) {
                  unlinkGuardianMutation.mutate(unlinkingGuardian.id);
                }
              }}
              disabled={unlinkGuardianMutation.isPending}
              className="text-xs bg-rose-600 hover:bg-rose-700 text-white rounded-lg"
            >
              {unlinkGuardianMutation.isPending
                ? t("common.removing", "Unlinking...")
                : t("students.unlinkGuardian", "Unlink")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Mobile App Login Credentials Dialog */}
      <Dialog open={isLoginModalOpen} onOpenChange={setIsLoginModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-emerald-800 dark:text-emerald-400" />
              <span>
                {student.has_app_account
                  ? t("students.resetAppPasswordTitle", "Reset Student App Password")
                  : t("students.setupAppLoginTitle", "Setup Student Mobile App Login")}
              </span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              {t(
                "students.setupAppLoginDesc",
                "Assign or update login credentials for this student to access the mobile app."
              )}
            </DialogDescription>
          </DialogHeader>

          {loginModalError && (
            <div className="rounded-lg border border-danger/20 bg-danger/10 p-2.5 text-xs text-danger font-medium">
              {loginModalError}
            </div>
          )}

          <div className="space-y-4 py-2">
            <FormField>
              <div className="flex items-center justify-between">
                <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  {t("students.loginPhone", "Student Mobile Number (Login ID)")}
                </FormLabel>
                {student.emergency_contact_phone && (
                  <button
                    type="button"
                    onClick={() => setLoginPhone(student.emergency_contact_phone || "")}
                    className="text-[11px] text-emerald-800 dark:text-emerald-400 hover:underline font-medium"
                  >
                    {t("students.copyEmergencyPhone", "Use emergency phone")}
                  </button>
                )}
              </div>
              <Input
                placeholder="+8801XXXXXXXXX"
                value={loginPhone}
                onChange={(e) => setLoginPhone(e.target.value)}
                className="h-9 text-xs font-mono rounded-lg"
              />
              <p className="text-[10px] text-slate-400 mt-1">
                {t("students.phoneLoginHint", "Student will use this phone number to log into the mobile app.")}
              </p>
            </FormField>

            <FormField>
              <div className="flex items-center justify-between">
                <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  {t("students.initialPassword", "Initial Password")}
                </FormLabel>
                <button
                  type="button"
                  onClick={handleGenerateStudentPassword}
                  className="inline-flex items-center gap-1 text-[11px] text-emerald-800 dark:text-emerald-400 hover:underline font-medium"
                >
                  <Sparkles className="h-3 w-3" />
                  <span>{t("common.generate", "Auto Generate")}</span>
                </button>
              </div>
              <div className="relative">
                <Input
                  type={showLoginPassword ? "text" : "password"}
                  placeholder="Min. 6 characters"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="h-9 text-xs rounded-lg pr-9 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowLoginPassword(!showLoginPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  aria-label={showLoginPassword ? "Hide password" : "Show password"}
                >
                  {showLoginPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                {t("students.passwordPolicyHint", "Student can use this initial password or change it later in their app.")}
              </p>
            </FormField>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLoginModalOpen(false)}
              className="text-xs rounded-lg"
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              size="sm"
              onClick={() => assignLoginMutation.mutate()}
              disabled={assignLoginMutation.isPending || !loginPassword || loginPassword.length < 6}
              className="text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
            >
              {assignLoginMutation.isPending
                ? t("common.saving", "Saving...")
                : student.has_app_account
                ? t("students.savePassword", "Update Password")
                : t("students.createLoginBtn", "Create App Login")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Student Dialog */}
      <EditStudentDialog
        open={isEditModalOpen}
        onOpenChange={setIsEditModalOpen}
        student={student}
      />

      {/* Delete Student Confirmation Dialog */}
      <ConfirmDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        title={t("students.deleteConfirmTitle", "Delete Student Profile")}
        description={t(
          "students.deleteConfirmDesc",
          "Are you sure you want to delete this student? Their profile and mobile app access will be deactivated. This action can be restored by an administrator."
        )}
        destructive
        loading={deleteMutation.isPending}
        confirmLabel={t("common.delete", "Delete")}
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  );
}
