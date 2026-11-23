import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowLeft,
  Edit2,
  Eye,
  EyeOff,
  KeyRound,
  Plus,
  Search,
  Smartphone,
  Sparkles,
  Trash2,
  UserCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { studentsApi, type GuardianItem } from "@/features/students/api/studentsApi";
import { Can } from "@/features/auth/permissions";
import { cn } from "@/lib/utils";
import { EditGuardianDialog } from "@/features/students/components/EditGuardianDialog";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";
import type { components } from "@/types/api";

type RelationType = components["schemas"]["RelationEnum"];

interface LinkedStudentDraft {
  studentId: string;
  studentName: string;
  studentIdNumber: string;
  relation: RelationType;
  isPrimary: boolean;
  canPickup: boolean;
  receivesSms: boolean;
  financialResponsible: boolean;
}

export function GuardiansListPage() {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const queryClient = useQueryClient();
  const { selectedSession } = useAcademicContextStore();

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // New Guardian Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [nameEn, setNameEn] = useState("");
  const [nameBn, setNameBn] = useState("");
  const [phone, setPhone] = useState("");
  const [nid, setNid] = useState("");
  const [occupation, setOccupation] = useState("");
  const [modalError, setModalError] = useState<string | null>(null);

  // App Login inside Add Modal
  const [givePortalAccess, setGivePortalAccess] = useState(false);
  const [initialPassword, setInitialPassword] = useState("");
  const [showInitialPassword, setShowInitialPassword] = useState(false);

  // Manage / Reset Guardian Login Modal State
  const [selectedGuardianForLogin, setSelectedGuardianForLogin] = useState<GuardianItem | null>(null);
  const [manageLoginPhone, setManageLoginPhone] = useState("");
  const [manageLoginPassword, setManageLoginPassword] = useState("");
  const [showManageLoginPassword, setShowManageLoginPassword] = useState(false);
  const [manageLoginError, setManageLoginError] = useState<string | null>(null);

  // Edit & Delete State
  const [selectedGuardianForEdit, setSelectedGuardianForEdit] = useState<GuardianItem | null>(null);
  const [selectedGuardianForDelete, setSelectedGuardianForDelete] = useState<GuardianItem | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => studentsApi.deleteGuardian(id),
    onSuccess: () => {
      toast.success(t("guardians.deleteSuccess", "Guardian record deleted successfully."));
      void queryClient.invalidateQueries({ queryKey: ["guardians"] });
      setSelectedGuardianForDelete(null);
    },
    onError: (err: unknown) => {
      toast.error((err as Error).message || "Failed to delete guardian.");
    },
  });

  // Student Linking inside Modal
  const [studentSearch, setStudentSearch] = useState("");
  const [selectedStudents, setSelectedStudents] = useState<LinkedStudentDraft[]>([]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["guardians", { search, page, session: selectedSession?.id }],
    queryFn: () => studentsApi.getGuardians({ search: search || undefined, page, session: selectedSession?.id }),
  });

  const guardians: GuardianItem[] = data?.results ?? [];
  const totalCount = data?.count ?? 0;

  // Search matching students to link
  const { data: searchStudentsData, isFetching: isSearchingStudents } = useQuery({
    queryKey: ["studentsSearch", studentSearch],
    queryFn: () => studentsApi.getStudents({ search: studentSearch, page: 1 }),
    enabled: isModalOpen && studentSearch.trim().length >= 2,
  });

  const searchedStudents = searchStudentsData?.results ?? [];

  const handleAddStudent = (s: { id: string; name_en: string; name_bn?: string; student_id: string }) => {
    if (selectedStudents.some((item) => item.studentId === s.id)) {
      return;
    }
    const isFirst = selectedStudents.length === 0;
    setSelectedStudents((prev) => [
      ...prev,
      {
        studentId: s.id,
        studentName: currentLang === "bn" && s.name_bn ? s.name_bn : s.name_en,
        studentIdNumber: s.student_id,
        relation: isFirst ? "father" : "other",
        isPrimary: isFirst,
        canPickup: true,
        receivesSms: true,
        financialResponsible: isFirst,
      },
    ]);
    setStudentSearch("");
  };

  const handleRemoveStudent = (studentId: string) => {
    setSelectedStudents((prev) => prev.filter((s) => s.studentId !== studentId));
  };

  const handleUpdateStudentDraft = (
    studentId: string,
    updates: Partial<LinkedStudentDraft>,
  ) => {
    setSelectedStudents((prev) =>
      prev.map((item) => {
        if (item.studentId === studentId) {
          return { ...item, ...updates };
        }
        // If this student is set to primary, clear primary on others
        if (updates.isPrimary) {
          return { ...item, isPrimary: false };
        }
        return item;
      }),
    );
  };

  const resetModalState = () => {
    setNameEn("");
    setNameBn("");
    setPhone("");
    setNid("");
    setOccupation("");
    setStudentSearch("");
    setSelectedStudents([]);
    setGivePortalAccess(false);
    setInitialPassword("");
    setModalError(null);
  };

  const handleGenerateGuardianPassword = () => {
    const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%";
    let pass = "";
    for (let i = 0; i < 8; i++) {
      pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setInitialPassword(pass);
  };

  const handleGenerateManagePassword = () => {
    const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%";
    let pass = "";
    for (let i = 0; i < 8; i++) {
      pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setManageLoginPassword(pass);
  };

  const createGuardianMutation = useMutation({
    mutationFn: () =>
      studentsApi.createGuardian({
        name_en: nameEn,
        name_bn: nameBn,
        phone,
        nid: nid || undefined,
        occupation: occupation || undefined,
        relation_default: selectedStudents[0]?.relation ?? "father",
        give_portal_access: givePortalAccess,
        initial_password: givePortalAccess ? initialPassword : undefined,
        student_links:
          selectedStudents.length > 0
            ? selectedStudents.map((s) => ({
                student_id: s.studentId,
                relation: s.relation,
                is_primary: s.isPrimary,
                can_pickup: s.canPickup,
                receives_sms: s.receivesSms,
                financial_responsible: s.financialResponsible,
              }))
            : undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["guardians"] });
      setIsModalOpen(false);
      resetModalState();
    },
    onError: (err: unknown) => {
      setModalError((err as Error).message || "Failed to create guardian.");
    },
  });

  const manageGuardianLoginMutation = useMutation({
    mutationFn: () => {
      if (!selectedGuardianForLogin) throw new Error("No guardian selected");
      if (!manageLoginPassword || manageLoginPassword.length < 6) {
        throw new Error("Password must be at least 6 characters.");
      }
      return studentsApi.createGuardianPortalAccount(selectedGuardianForLogin.id, {
        phone: manageLoginPhone || undefined,
        password: manageLoginPassword,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["guardians"] });
      setSelectedGuardianForLogin(null);
      setManageLoginPassword("");
      setManageLoginError(null);
    },
    onError: (err: unknown) => {
      setManageLoginError((err as Error).message || "Failed to set guardian login credentials.");
    },
  });

  return (
    <div className="space-y-6">
      {/* Return & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("students.guardiansDirectory", "Guardians Directory")}
            </h1>
            <span className="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 text-xs font-bold text-slate-700 dark:text-slate-300">
              {totalCount} {t("students.guardiansTotal", "Guardians")}
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-500">
            {t("students.guardiansSubtitle", "Household contacts, emergency contacts, and parent portal access.")}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/students"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 rounded-lg shadow-2xs"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>{t("students.backToDirectory", "Student Directory")}</span>
          </Link>

          <Can perm="students.manage">
            <Button
              size="sm"
              onClick={() => {
                resetModalState();
                setIsModalOpen(true);
              }}
              className="gap-1.5 text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>{t("students.newGuardian", "Add Guardian")}</span>
            </Button>
          </Can>
        </div>
      </div>

      {/* Search Bar */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5 shadow-2xs">
        <div className="relative max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("students.searchGuardians", "Search by name or mobile number...")}
            className="h-9 pl-9 text-xs rounded-lg border-slate-200 dark:border-slate-800"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">{t("students.guardian", "Guardian Name")}</th>
              <th className="px-4 py-3">{t("students.phone", "Mobile Number")}</th>
              <th className="px-4 py-3">{t("students.nid", "NID Number")}</th>
              <th className="px-4 py-3">{t("students.occupation", "Occupation")}</th>
              <th className="px-4 py-3">{t("students.linkedStudents", "Linked Students")}</th>
              <th className="px-4 py-3 text-right">{t("common.actions", "Actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-400">
                  <div className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                    <span>{t("common.loading", "Loading guardians...")}</span>
                  </div>
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-danger">
                  <div className="flex flex-col items-center gap-2">
                    <span>{t("common.errorLoading", "Failed to load guardians.")}</span>
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
                  </div>
                </td>
              </tr>
            ) : guardians.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-16 text-center text-slate-400">
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                    {selectedSession
                      ? t("students.noGuardiansInSession", `No guardians found for students in ${selectedSession.name}`)
                      : t("students.noGuardians", "No guardians registered yet.")}
                  </p>
                  <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
                    {search
                      ? t("students.adjustFilters", "Try adjusting your search criteria or filters.")
                      : t(
                          "students.noGuardiansInSessionDesc",
                          "Guardians are linked to students enrolled in this session. Once students are enrolled, their guardians will appear here."
                        )}
                  </p>
                </td>
              </tr>
            ) : (
              guardians.map((g) => (
                <tr key={g.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {currentLang === "bn" && g.name_bn ? g.name_bn : g.name_en}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-mono font-medium text-slate-700 dark:text-slate-300">
                      {g.phone}
                    </div>
                    <div className="mt-0.5">
                      {g.has_portal_account ? (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-200 dark:border-emerald-800">
                          <Smartphone className="h-2.5 w-2.5" />
                          <span>{t("students.loginActive", "App Active")}</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-1.5 py-0.2 rounded border border-amber-200 dark:border-amber-800">
                          <span>{t("students.noLogin", "No App Login")}</span>
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-500">
                    {g.nid || "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                    {g.occupation || "—"}
                  </td>
                  <td className="px-4 py-3">
                    {g.student_relations && g.student_relations.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 max-w-sm">
                        {g.student_relations.map((rel) => (
                          <Link
                            key={rel.id}
                            to={`/students/${rel.student}`}
                            className="inline-flex items-center gap-1 rounded-md bg-slate-100 hover:bg-emerald-50 hover:text-emerald-800 dark:bg-slate-800 dark:hover:bg-emerald-950 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition-colors"
                            title={`${rel.student_name} (${rel.relation})`}
                          >
                            <span>{rel.student_name}</span>
                            {rel.student_id_number && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                ({rel.student_id_number})
                              </span>
                            )}
                            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold capitalize">
                              • {rel.relation}
                            </span>
                            {rel.is_primary && (
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" title={t("students.isPrimary", "Primary Contact")} />
                            )}
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Can perm="students.manage">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant={g.has_portal_account ? "ghost" : "default"}
                          size="sm"
                          onClick={() => {
                            setSelectedGuardianForLogin(g);
                            setManageLoginPhone(g.phone);
                            setManageLoginPassword("");
                            setManageLoginError(null);
                          }}
                          className={cn(
                            "h-8 gap-1.5 text-xs rounded-lg",
                            g.has_portal_account
                              ? "text-emerald-800 dark:text-emerald-400 hover:bg-emerald-50"
                              : "bg-emerald-800 hover:bg-emerald-900 text-white font-semibold"
                          )}
                        >
                          <KeyRound className="h-3.5 w-3.5" />
                          <span>
                            {g.has_portal_account
                              ? t("students.resetPassword", "Reset Password")
                              : t("students.createLoginDetails", "Create Login Details")}
                          </span>
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedGuardianForEdit(g)}
                          className="h-8 w-8 p-0 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
                          title={t("common.edit", "Edit")}
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedGuardianForDelete(g)}
                          className="h-8 w-8 p-0 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg"
                          title={t("common.delete", "Delete")}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </Can>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalCount > 20 && (
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{t("common.total", "Total")}: {totalCount}</span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="text-xs"
            >
              {t("common.previous", "Previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page * 20 >= totalCount}
              onClick={() => setPage((p) => p + 1)}
              className="text-xs"
            >
              {t("common.next", "Next")}
            </Button>
          </div>
        </div>
      )}

      {/* Add Guardian Dialog */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100">
              {t("students.addGuardian", "Add Guardian Record")}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              {t("students.addGuardianSubtitle", "Enter guardian demographics to link with student profiles.")}
            </DialogDescription>
          </DialogHeader>

          {modalError && (
            <div className="rounded-lg border border-danger/20 bg-danger/10 p-2.5 text-xs text-danger font-medium">
              {modalError}
            </div>
          )}

          <div className="space-y-4 py-2">
            {/* Demographics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <FormField>
                <FormLabel required className="text-xs font-medium text-slate-700">
                  {t("students.nameEn", "Full Name (English)")}
                </FormLabel>
                <Input
                  value={nameEn}
                  onChange={(e) => setNameEn(e.target.value)}
                  placeholder="e.g. Rafiqul Islam"
                  className="h-9 text-xs rounded-lg"
                />
              </FormField>

              <FormField>
                <FormLabel required className="text-xs font-medium text-slate-700">
                  {t("students.nameBn", "Full Name (Bangla)")}
                </FormLabel>
                <Input
                  value={nameBn}
                  onChange={(e) => setNameBn(e.target.value)}
                  placeholder="e.g. রফিকুল ইসলাম"
                  className="h-9 text-xs rounded-lg"
                />
              </FormField>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <FormField>
                <FormLabel required className="text-xs font-medium text-slate-700">
                  {t("students.phone", "Mobile Number")}
                </FormLabel>
                <Input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+8801XXXXXXXXX"
                  className="h-9 text-xs font-mono rounded-lg"
                />
              </FormField>

              <FormField>
                <FormLabel className="text-xs font-medium text-slate-700">
                  {t("students.nid", "NID Number")}
                </FormLabel>
                <Input
                  value={nid}
                  onChange={(e) => setNid(e.target.value)}
                  placeholder="e.g. 1985123456789"
                  className="h-9 text-xs font-mono rounded-lg"
                />
              </FormField>

              <FormField>
                <FormLabel className="text-xs font-medium text-slate-700">
                  {t("students.occupation", "Occupation")}
                </FormLabel>
                <Input
                  value={occupation}
                  onChange={(e) => setOccupation(e.target.value)}
                  placeholder="e.g. Service, Business"
                  className="h-9 text-xs rounded-lg"
                />
              </FormField>
            </div>

            {/* Mobile App Login Credentials Section in Modal */}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Smartphone className="h-4 w-4 text-emerald-800 dark:text-emerald-400" />
                  <div>
                    <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                      {t("students.appLoginSection", "Mobile App & Portal Login")}
                    </h4>
                    <p className="text-[11px] text-slate-500">
                      {t("students.guardianAppLoginHelp", "Allow this guardian to log into the mobile app using their phone number.")}
                    </p>
                  </div>
                </div>

                <label className="inline-flex items-center gap-2 cursor-pointer select-none bg-slate-50 dark:bg-slate-800/60 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700">
                  <input
                    type="checkbox"
                    checked={givePortalAccess}
                    onChange={(e) => setGivePortalAccess(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-300 text-emerald-800 focus:ring-emerald-700"
                  />
                  <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                    {t("students.giveAppAccess", "Grant App Access (লগইন দিন)")}
                  </span>
                </label>
              </div>

              {givePortalAccess && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
                  <div>
                    <span className="text-xs font-medium text-slate-700 dark:text-slate-300 block mb-1">
                      {t("students.loginPhone", "Login Mobile Number")}
                    </span>
                    <div className="h-9 px-3 text-xs font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 flex items-center text-slate-700 dark:text-slate-300">
                      {phone || t("students.enterPhoneAbove", "Enter mobile number above")}
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        {t("students.initialPassword", "Initial Password")} *
                      </span>
                      <button
                        type="button"
                        onClick={handleGenerateGuardianPassword}
                        className="inline-flex items-center gap-1 text-[11px] text-emerald-800 dark:text-emerald-400 hover:underline font-medium"
                      >
                        <Sparkles className="h-3 w-3" />
                        <span>{t("common.generate", "Auto Generate")}</span>
                      </button>
                    </div>
                    <div className="relative">
                      <Input
                        type={showInitialPassword ? "text" : "password"}
                        placeholder="Min. 6 characters"
                        value={initialPassword}
                        onChange={(e) => setInitialPassword(e.target.value)}
                        className="h-9 text-xs rounded-lg pr-8 font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => setShowInitialPassword(!showInitialPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        aria-label={showInitialPassword ? "Hide password" : "Show password"}
                      >
                        {showInitialPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Link Students Section */}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                    <UserCheck className="h-3.5 w-3.5 text-emerald-600" />
                    <span>{t("students.linkedStudents", "Linked Students")}</span>
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    {t("students.linkStudentsHelp", "Select one or more students to link with this guardian.")}
                  </p>
                </div>
                {selectedStudents.length > 0 && (
                  <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 dark:bg-emerald-950 px-2 py-0.5 rounded-full">
                    {selectedStudents.length} {t("students.selected", "selected")}
                  </span>
                )}
              </div>

              {/* Student Search to Link */}
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                <Input
                  value={studentSearch}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  placeholder={t("students.searchStudentsToLink", "Search student by name or student ID...")}
                  className="h-9 pl-9 text-xs rounded-lg"
                />
                {isSearchingStudents && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-400">
                    {t("common.searching", "Searching...")}
                  </span>
                )}
              </div>

              {/* Autocomplete Results */}
              {studentSearch.trim().length >= 2 && searchedStudents.length > 0 && (
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-1.5 max-h-40 overflow-y-auto space-y-1">
                  {searchedStudents.map((st) => {
                    const isAlreadySelected = selectedStudents.some(
                      (item) => item.studentId === st.id,
                    );
                    return (
                      <div
                        key={st.id}
                        className="flex items-center justify-between px-2.5 py-1.5 rounded-md hover:bg-white dark:hover:bg-slate-800 transition-colors text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            {currentLang === "bn" && st.name_bn ? st.name_bn : st.name_en}
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">
                            ({st.student_id})
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant={isAlreadySelected ? "ghost" : "outline"}
                          disabled={isAlreadySelected}
                          onClick={() => handleAddStudent(st)}
                          className="h-6 px-2 text-[11px]"
                        >
                          {isAlreadySelected ? t("common.added", "Added") : `+ ${t("students.linkStudent", "Link")}`}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Selected Students List */}
              {selectedStudents.length > 0 ? (
                <div className="space-y-2.5">
                  {selectedStudents.map((s) => (
                    <div
                      key={s.studentId}
                      className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 p-3 space-y-2.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                            {s.studentName}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            ({s.studentIdNumber})
                          </span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveStudent(s.studentId)}
                          className="h-6 w-6 p-0 text-slate-400 hover:text-rose-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 items-center">
                        <div>
                          <FormLabel className="text-[11px] font-medium text-slate-600">
                            {t("students.relation", "Relationship")}
                          </FormLabel>
                          <Select
                            value={s.relation}
                            onValueChange={(val) =>
                              handleUpdateStudentDraft(s.studentId, {
                                relation: val as RelationType,
                              })
                            }
                          >
                            <SelectTrigger className="h-8 text-xs rounded-lg bg-white dark:bg-slate-900">
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
                        </div>

                        <div className="grid grid-cols-2 gap-1.5 pt-3">
                          <label className="flex items-center gap-1.5 text-[11px] text-slate-700 dark:text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={s.isPrimary}
                              onChange={(e) =>
                                handleUpdateStudentDraft(s.studentId, {
                                  isPrimary: e.target.checked,
                                })
                              }
                              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5"
                            />
                            <span>{t("students.isPrimary", "Primary")}</span>
                          </label>

                          <label className="flex items-center gap-1.5 text-[11px] text-slate-700 dark:text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={s.canPickup}
                              onChange={(e) =>
                                handleUpdateStudentDraft(s.studentId, {
                                  canPickup: e.target.checked,
                                })
                              }
                              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5"
                            />
                            <span>{t("students.canPickup", "Pickup")}</span>
                          </label>

                          <label className="flex items-center gap-1.5 text-[11px] text-slate-700 dark:text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={s.receivesSms}
                              onChange={(e) =>
                                handleUpdateStudentDraft(s.studentId, {
                                  receivesSms: e.target.checked,
                                })
                              }
                              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5"
                            />
                            <span>{t("students.receivesSms", "SMS")}</span>
                          </label>

                          <label className="flex items-center gap-1.5 text-[11px] text-slate-700 dark:text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={s.financialResponsible}
                              onChange={(e) =>
                                handleUpdateStudentDraft(s.studentId, {
                                  financialResponsible: e.target.checked,
                                })
                              }
                              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5"
                            />
                            <span>{t("students.financialResponsible", "Finance")}</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-200 dark:border-slate-800 p-3 text-center text-xs text-slate-400">
                  {t("students.noStudentsSelected", "No students selected yet. Search above to link students.")}
                </div>
              )}
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                resetModalState();
                setIsModalOpen(false);
              }}
              className="text-xs rounded-lg"
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              size="sm"
              onClick={() => createGuardianMutation.mutate()}
              disabled={createGuardianMutation.isPending || !nameEn || !nameBn || !phone}
              className="text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
            >
              {createGuardianMutation.isPending
                ? t("common.saving", "Saving...")
                : t("common.save", "Save Guardian")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Manage / Reset Guardian App Login Dialog */}
      <Dialog
        open={Boolean(selectedGuardianForLogin)}
        onOpenChange={(open) => !open && setSelectedGuardianForLogin(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-emerald-800 dark:text-emerald-400" />
              <span>
                {selectedGuardianForLogin?.has_portal_account
                  ? t("students.resetGuardianPasswordTitle", "Reset Guardian App Password")
                  : t("students.setupGuardianLoginTitle", "Setup Guardian Mobile App Login")}
              </span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              {t(
                "students.setupGuardianLoginDesc",
                "Assign or update login credentials for this guardian to access the parent mobile app."
              )}
            </DialogDescription>
          </DialogHeader>

          {manageLoginError && (
            <div className="rounded-lg border border-danger/20 bg-danger/10 p-2.5 text-xs text-danger font-medium">
              {manageLoginError}
            </div>
          )}

          {selectedGuardianForLogin && (
            <div className="space-y-4 py-2">
              <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3 text-xs border border-slate-200 dark:border-slate-700">
                <span className="text-slate-400 block">{t("students.guardianName", "Guardian Name")}</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                  {selectedGuardianForLogin.name_en}
                </span>
              </div>

              <FormField>
                <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  {t("students.loginPhone", "Guardian Mobile Number (Login ID)")}
                </FormLabel>
                <Input
                  placeholder="+8801XXXXXXXXX"
                  value={manageLoginPhone}
                  onChange={(e) => setManageLoginPhone(e.target.value)}
                  className="h-9 text-xs font-mono rounded-lg"
                />
                <p className="text-[10px] text-slate-400 mt-1">
                  {t("students.guardianPhoneLoginHint", "Guardian will use this phone number to sign in.")}
                </p>
              </FormField>

              <FormField>
                <div className="flex items-center justify-between">
                  <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    {t("students.initialPassword", "Initial Password")}
                  </FormLabel>
                  <button
                    type="button"
                    onClick={handleGenerateManagePassword}
                    className="inline-flex items-center gap-1 text-[11px] text-emerald-800 dark:text-emerald-400 hover:underline font-medium"
                  >
                    <Sparkles className="h-3 w-3" />
                    <span>{t("common.generate", "Auto Generate")}</span>
                  </button>
                </div>
                <div className="relative">
                  <Input
                    type={showManageLoginPassword ? "text" : "password"}
                    placeholder="Min. 6 characters"
                    value={manageLoginPassword}
                    onChange={(e) => setManageLoginPassword(e.target.value)}
                    className="h-9 text-xs rounded-lg pr-9 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowManageLoginPassword(!showManageLoginPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    aria-label={showManageLoginPassword ? "Hide password" : "Show password"}
                  >
                    {showManageLoginPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  {t("students.guardianPasswordHint", "Guardian can use this initial password or change it in the mobile app.")}
                </p>
              </FormField>
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedGuardianForLogin(null)}
              className="text-xs rounded-lg"
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              size="sm"
              onClick={() => manageGuardianLoginMutation.mutate()}
              disabled={
                manageGuardianLoginMutation.isPending ||
                !manageLoginPassword ||
                manageLoginPassword.length < 6
              }
              className="text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
            >
              {manageGuardianLoginMutation.isPending
                ? t("common.saving", "Saving...")
                : selectedGuardianForLogin?.has_portal_account
                ? t("students.savePassword", "Update Password")
                : t("students.createLoginBtn", "Create App Login")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Guardian Dialog */}
      <EditGuardianDialog
        open={Boolean(selectedGuardianForEdit)}
        onOpenChange={(open) => {
          if (!open) setSelectedGuardianForEdit(null);
        }}
        guardian={selectedGuardianForEdit}
      />

      {/* Delete Guardian Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(selectedGuardianForDelete)}
        onOpenChange={(open) => {
          if (!open) setSelectedGuardianForDelete(null);
        }}
        title={t("guardians.deleteConfirmTitle", "Delete Guardian Profile")}
        description={t(
          "guardians.deleteConfirmDesc",
          "Are you sure you want to delete this guardian? Their profile and parent portal login will be deactivated. This action can be restored by an administrator."
        )}
        destructive
        loading={deleteMutation.isPending}
        confirmLabel={t("common.delete", "Delete")}
        onConfirm={() => {
          if (selectedGuardianForDelete) {
            deleteMutation.mutate(selectedGuardianForDelete.id);
          }
        }}
      />
    </div>
  );
}
