import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CreditCard,
  History,
  Plus,
  User,
} from "lucide-react";
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
import { Can } from "@/features/auth/permissions";

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
          <div className="flex items-center gap-2.5">
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
    </div>
  );
}
