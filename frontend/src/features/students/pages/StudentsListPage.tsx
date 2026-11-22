import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Download,
  Edit2,
  Plus,
  RotateCcw,
  Search,
  Smartphone,
  Trash2,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { studentsApi, type StudentListItem } from "@/features/students/api/studentsApi";
import { Can } from "@/features/auth/permissions";
import { EditStudentDialog } from "@/features/students/components/EditStudentDialog";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";

export function StudentsListPage() {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const navigate = useNavigate();

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [genderFilter, setGenderFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [page, setPage] = useState(1);

  const queryClient = useQueryClient();
  const [selectedStudentForEdit, setSelectedStudentForEdit] = useState<StudentListItem | null>(null);
  const [selectedStudentForDelete, setSelectedStudentForDelete] = useState<StudentListItem | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => studentsApi.deleteStudent(id),
    onSuccess: () => {
      toast.success(t("students.deleteSuccess", "Student deleted successfully."));
      void queryClient.invalidateQueries({ queryKey: ["students"] });
      setSelectedStudentForDelete(null);
    },
    onError: (err: unknown) => {
      toast.error((err as Error).message || "Failed to delete student.");
    },
  });

  // TanStack Query for student list
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["students", { search: debouncedSearch, gender: genderFilter, status: statusFilter, page }],
    queryFn: () =>
      studentsApi.getStudents({
        search: debouncedSearch || undefined,
        gender: genderFilter !== "ALL" ? genderFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        page,
      }),
  });

  const students: StudentListItem[] = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const pageSize = 20;
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  const handleSearchChange = (val: string) => {
    setSearch(val);
    // Simple debounce trigger
    const timeout = setTimeout(() => {
      setDebouncedSearch(val.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timeout);
  };

  const handleResetFilters = () => {
    setSearch("");
    setDebouncedSearch("");
    setGenderFilter("ALL");
    setStatusFilter("ALL");
    setPage(1);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
            {t("common.active", "Active")}
          </span>
        );
      case "inactive":
        return (
          <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
            {t("common.inactive", "Inactive")}
          </span>
        );
      case "transferred":
        return (
          <span className="inline-flex items-center rounded-md bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60">
            {t("students.transferred", "Transferred")}
          </span>
        );
      case "graduated":
        return (
          <span className="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-950/60 px-2 py-0.5 text-xs font-semibold text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800/60">
            {t("students.graduated", "Graduated")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-600">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("nav.students", "Student Directory")}
            </h1>
            <span className="inline-flex items-center rounded-full bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 px-2.5 py-0.5 text-xs font-bold text-emerald-800 dark:text-emerald-300">
              {totalCount} {t("students.enrolledTotal", "Students")}
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-500">
            {t("students.subtitle", "Academic roster, demographic records, and enrollment status.")}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <a
            href={studentsApi.getExportUrl()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 shadow-2xs transition-all"
            download
          >
            <Download className="h-3.5 w-3.5" />
            <span>{t("common.export", "Export Excel")}</span>
          </a>

          <Can perm="students.manage">
            <Button
              size="sm"
              onClick={() => {
                void navigate("/students/new");
              }}
              className="gap-1.5 text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>{t("students.newStudent", "New Student Admission")}</span>
            </Button>
          </Can>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5 shadow-2xs">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
          {/* Search Field */}
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder={t("students.searchPlaceholder", "Search by name, student ID, or birth reg number...")}
              className="h-9 pl-9 text-xs rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
            />
          </div>

          {/* Gender Filter */}
          <div className="w-full md:w-36">
            <Select value={genderFilter} onValueChange={(val) => { setGenderFilter(val); setPage(1); }}>
              <SelectTrigger className="h-9 text-xs rounded-lg border-slate-200 dark:border-slate-800">
                <SelectValue placeholder={t("students.gender", "Gender")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">{t("common.allGenders", "All Genders")}</SelectItem>
                <SelectItem value="male" className="text-xs">{t("students.male", "Male")}</SelectItem>
                <SelectItem value="female" className="text-xs">{t("students.female", "Female")}</SelectItem>
                <SelectItem value="other" className="text-xs">{t("students.other", "Other")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Status Filter */}
          <div className="w-full md:w-36">
            <Select value={statusFilter} onValueChange={(val) => { setStatusFilter(val); setPage(1); }}>
              <SelectTrigger className="h-9 text-xs rounded-lg border-slate-200 dark:border-slate-800">
                <SelectValue placeholder={t("common.status", "Status")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">{t("common.allStatus", "All Status")}</SelectItem>
                <SelectItem value="active" className="text-xs">{t("common.active", "Active")}</SelectItem>
                <SelectItem value="inactive" className="text-xs">{t("common.inactive", "Inactive")}</SelectItem>
                <SelectItem value="transferred" className="text-xs">{t("students.transferred", "Transferred")}</SelectItem>
                <SelectItem value="graduated" className="text-xs">{t("students.graduated", "Graduated")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Reset Button */}
          {(debouncedSearch || genderFilter !== "ALL" || statusFilter !== "ALL") && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetFilters}
              className="h-9 px-2.5 text-xs text-slate-500 hover:text-slate-800 rounded-lg"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1" />
              <span>{t("common.reset", "Reset")}</span>
            </Button>
          )}
        </div>
      </div>

      {/* Student Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">{t("students.student", "Student")}</th>
                <th className="px-4 py-3">{t("students.placement", "Current Placement")}</th>
                <th className="px-4 py-3">{t("students.genderBlood", "Gender & Blood")}</th>
                <th className="px-4 py-3">{t("students.religion", "Religion")}</th>
                <th className="px-4 py-3">{t("common.status", "Status")}</th>
                <th className="px-4 py-3 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <div className="inline-flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                      <span>{t("common.loading", "Loading student roster...")}</span>
                    </div>
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-danger">
                    <span>{t("common.errorLoading", "Failed to load student roster.")}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void refetch()}
                      className="ml-2 text-xs"
                    >
                      {t("common.retry", "Retry")}
                    </Button>
                  </td>
                </tr>
              ) : students.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-400 mb-3">
                      <Users className="h-6 w-6" />
                    </div>
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                      {t("students.noStudentsFound", "No students found")}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {debouncedSearch || genderFilter !== "ALL" || statusFilter !== "ALL"
                        ? t("students.adjustFilters", "Try adjusting your search criteria or filters.")
                        : t("students.getStarted", "Begin by admitting or enrolling new students.")}
                    </p>
                  </td>
                </tr>
              ) : (
                students.map((student) => {
                  const enrollment = student.active_enrollment as {
                    class_name: string;
                    section_name: string;
                    roll_no: number;
                    session_name: string;
                  } | null;
                  return (
                    <tr
                      key={student.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {/* Student Identity */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 shrink-0 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/80 dark:border-emerald-800 flex items-center justify-center font-bold text-xs text-emerald-800 dark:text-emerald-300">
                            {student.name_en.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <Link
                              to={`/students/${student.id}`}
                              className="font-bold text-slate-900 dark:text-slate-100 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors"
                            >
                              {currentLang === "bn" && student.name_bn ? student.name_bn : student.name_en}
                            </Link>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[11px] font-mono text-slate-400">
                                {student.student_id}
                              </span>
                              {student.has_app_account ? (
                                <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-200 dark:border-emerald-800">
                                  <Smartphone className="h-2.5 w-2.5" />
                                  <span>{student.phone || "App"}</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-1.5 py-0.2 rounded border border-amber-200 dark:border-amber-800">
                                  <span>{t("students.noAppLogin", "No App")}</span>
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Current Placement */}
                      <td className="px-4 py-3">
                        {enrollment ? (
                          <div className="space-y-0.5">
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                              {enrollment.class_name} • {enrollment.section_name}
                            </span>
                            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                              <span className="inline-flex items-center rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.2 font-mono font-medium">
                                Roll {enrollment.roll_no}
                              </span>
                              <span>({enrollment.session_name})</span>
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-xs italic">
                            {t("students.notEnrolled", "Not enrolled")}
                          </span>
                        )}
                      </td>

                      {/* Gender & Blood Group */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <span className="capitalize text-slate-700 dark:text-slate-300">
                            {student.gender}
                          </span>
                          {student.blood_group && (
                            <span className="inline-flex items-center rounded bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900/50 px-1.5 py-0.2 text-[10px] font-semibold">
                              {student.blood_group}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Religion */}
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400 capitalize">
                        {student.religion || "—"}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3">
                        {getStatusBadge(student.status ?? "active")}
                      </td>

                      {/* Action */}
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              void navigate(`/students/${student.id}`);
                            }}
                            className="h-8 px-2 text-xs text-emerald-800 dark:text-emerald-400 hover:text-emerald-900 hover:bg-emerald-50 rounded-lg"
                            title={t("common.view", "View")}
                          >
                            <span>{t("common.view", "View")}</span>
                            <span className="ml-1">&rarr;</span>
                          </Button>

                          <Can perm="students.manage">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedStudentForEdit(student)}
                              className="h-8 w-8 p-0 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
                              title={t("common.edit", "Edit")}
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </Button>

                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedStudentForDelete(student)}
                              className="h-8 w-8 p-0 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg"
                              title={t("common.delete", "Delete")}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </Can>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="border-t border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center justify-between text-xs text-slate-500">
            <span>
              {t("common.page", "Page")} {page} {t("common.of", "of")} {totalPages}
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="h-8 px-3 text-xs rounded-lg"
              >
                {t("common.prev", "Previous")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="h-8 px-3 text-xs rounded-lg"
              >
                {t("common.next", "Next")}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Edit Student Dialog */}
      <EditStudentDialog
        open={Boolean(selectedStudentForEdit)}
        onOpenChange={(open) => {
          if (!open) setSelectedStudentForEdit(null);
        }}
        student={selectedStudentForEdit}
      />

      {/* Delete Student Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(selectedStudentForDelete)}
        onOpenChange={(open) => {
          if (!open) setSelectedStudentForDelete(null);
        }}
        title={t("students.deleteConfirmTitle", "Delete Student Profile")}
        description={t(
          "students.deleteConfirmDesc",
          "Are you sure you want to delete this student? Their profile and mobile app access will be deactivated. This action can be restored by an administrator."
        )}
        destructive
        loading={deleteMutation.isPending}
        confirmLabel={t("common.delete", "Delete")}
        onConfirm={() => {
          if (selectedStudentForDelete) {
            deleteMutation.mutate(selectedStudentForDelete.id);
          }
        }}
      />
    </div>
  );
}
