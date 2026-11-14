import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Building2,
  Award,
  Plus,
  Search,
  X,
  AlertCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { staffApi } from "@/features/staff/api/staffApi";
import {
  departmentSchema,
  designationSchema,
  type DepartmentFormData,
  type DesignationFormData,
} from "@/features/staff/schemas/staffSchemas";

type ActiveTab = "departments" | "designations";

export default function DepartmentsDesignationsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<ActiveTab>("departments");
  const [search, setSearch] = useState("");
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [showDesigModal, setShowDesigModal] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Departments Query
  const {
    data: departmentsData,
    isLoading: isDeptLoading,
  } = useQuery({
    queryKey: ["departments", search],
    queryFn: () => staffApi.getDepartments({ search: search.trim() || undefined }),
    enabled: activeTab === "departments",
  });

  // Designations Query
  const {
    data: designationsData,
    isLoading: isDesigLoading,
  } = useQuery({
    queryKey: ["designations", search],
    queryFn: () => staffApi.getDesignations({ search: search.trim() || undefined }),
    enabled: activeTab === "designations",
  });

  // Department Form
  const {
    register: registerDept,
    handleSubmit: handleDeptSubmit,
    reset: resetDept,
    formState: { errors: deptErrors, isSubmitting: isDeptSubmitting },
  } = useForm<DepartmentFormData>({
    resolver: zodResolver(departmentSchema),
  });

  // Designation Form
  const {
    register: registerDesig,
    handleSubmit: handleDesigSubmit,
    reset: resetDesig,
    formState: { errors: desigErrors, isSubmitting: isDesigSubmitting },
  } = useForm<DesignationFormData>({
    resolver: zodResolver(designationSchema) as never,
    defaultValues: {
      rank_order: 1,
      role_category: "teacher",
    },
  });

  // Create Department Mutation
  const createDeptMutation = useMutation({
    mutationFn: (data: DepartmentFormData) =>
      staffApi.createDepartment({
        name: data.name,
        code: data.code,
        description: data.description || "",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["departments"] });
      resetDept();
      setShowDeptModal(false);
      setActionError(null);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to create department";
      setActionError(msg);
    },
  });

  // Create Designation Mutation
  const createDesigMutation = useMutation({
    mutationFn: (data: DesignationFormData) =>
      staffApi.createDesignation({
        title: data.title,
        title_bn: data.title_bn || "",
        code: data.code,
        rank_order: Number(data.rank_order),
        role_category: data.role_category,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["designations"] });
      resetDesig();
      setShowDesigModal(false);
      setActionError(null);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to create designation";
      setActionError(msg);
    },
  });

  const departments = departmentsData?.results ?? [];
  const designations = designationsData?.results ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {t("staff.deptAndDesigTitle", "Departments & Designations")}
          </h1>
          <p className="text-xs text-slate-500">
            {t(
              "staff.deptAndDesigSubtitle",
              "Manage institutional hierarchy, faculties, and official staff designations."
            )}
          </p>
        </div>

        <div>
          {activeTab === "departments" ? (
            <Button
              onClick={() => {
                setActionError(null);
                setShowDeptModal(true);
              }}
              className="gap-2 bg-emerald-800 text-xs hover:bg-emerald-900 text-white rounded-lg h-9 shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>{t("staff.addDepartment", "Add Department")}</span>
            </Button>
          ) : (
            <Button
              onClick={() => {
                setActionError(null);
                setShowDesigModal(true);
              }}
              className="gap-2 bg-emerald-800 text-xs hover:bg-emerald-900 text-white rounded-lg h-9 shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>{t("staff.addDesignation", "Add Designation")}</span>
            </Button>
          )}
        </div>
      </div>

      {/* Tabs & Search */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-1">
          <button
            onClick={() => {
              setActiveTab("departments");
              setSearch("");
            }}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "departments"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Building2 className="h-4 w-4" />
            {t("staff.departments", "Departments")}
          </button>
          <button
            onClick={() => {
              setActiveTab("designations");
              setSearch("");
            }}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "designations"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Award className="h-4 w-4" />
            {t("staff.designations", "Designations")}
          </button>
        </div>

        <div className="relative w-64">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={
              activeTab === "departments"
                ? t("staff.searchDepts", "Search departments...")
                : t("staff.searchDesigs", "Search designations...")
            }
            className="pl-8 text-xs h-8 rounded-lg"
          />
        </div>
      </div>

      {/* Tab 1: Departments Table */}
      {activeTab === "departments" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          {isDeptLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
            </div>
          ) : departments.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              {t("staff.noDepartments", "No departments found.")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("staff.deptCode", "Code")}</th>
                    <th className="px-4 py-3 font-semibold">{t("staff.deptName", "Department Name")}</th>
                    <th className="px-4 py-3 font-semibold">{t("staff.deptHead", "Head of Department")}</th>
                    <th className="px-4 py-3 font-semibold">{t("common.description", "Description")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {departments.map((dept) => (
                    <tr key={dept.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-mono font-bold text-emerald-800 dark:text-emerald-400">
                        {dept.code}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        {dept.name}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {dept.head_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-500 max-w-[300px] truncate">
                        {dept.description || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Designations Table */}
      {activeTab === "designations" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          {isDesigLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
            </div>
          ) : designations.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              {t("staff.noDesignations", "No designations found.")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-semibold text-center">{t("staff.rank", "Rank")}</th>
                    <th className="px-4 py-3 font-semibold">{t("staff.desigCode", "Code")}</th>
                    <th className="px-4 py-3 font-semibold">{t("staff.titleEn", "Title (EN)")}</th>
                    <th className="px-4 py-3 font-semibold">{t("staff.titleBn", "Title (BN)")}</th>
                    <th className="px-4 py-3 font-semibold">{t("staff.roleCategory", "Category")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {designations.map((desig) => (
                    <tr key={desig.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3 text-center font-mono font-bold text-slate-500">
                        #{desig.rank_order}
                      </td>
                      <td className="px-4 py-3 font-mono font-bold text-emerald-800 dark:text-emerald-400">
                        {desig.code}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        {desig.title}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {desig.title_bn || "—"}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-bold capitalize text-slate-700 dark:text-slate-300">
                          {desig.role_category}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal: Add Department */}
      {showDeptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {t("staff.addDepartment", "Add New Department")}
              </h2>
              <button
                onClick={() => setShowDeptModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {actionError && (
              <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <form
              onSubmit={(e) => {
                void handleDeptSubmit((data) => createDeptMutation.mutate(data))(e);
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.deptName", "Department Name")} *
                </label>
                <Input
                  {...registerDept("name")}
                  placeholder="e.g. Department of Science"
                  className="h-9 text-xs"
                />
                {deptErrors.name && (
                  <p className="mt-1 text-[11px] text-rose-600">{deptErrors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.deptCode", "Department Code")} *
                </label>
                <Input
                  {...registerDept("code")}
                  placeholder="e.g. SCI"
                  className="h-9 text-xs font-mono uppercase"
                />
                {deptErrors.code && (
                  <p className="mt-1 text-[11px] text-rose-600">{deptErrors.code.message}</p>
                )}
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("common.description", "Description")}
                </label>
                <textarea
                  {...registerDept("description")}
                  rows={3}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                  placeholder="Optional brief notes about this department..."
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDeptModal(false)}
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isDeptSubmitting || createDeptMutation.isPending}
                  className="bg-emerald-800 hover:bg-emerald-900 text-white"
                >
                  {isDeptSubmitting ? t("common.saving", "Saving...") : t("common.save", "Save")}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Designation */}
      {showDesigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {t("staff.addDesignation", "Add New Designation")}
              </h2>
              <button
                onClick={() => setShowDesigModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {actionError && (
              <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <form
              onSubmit={(e) => {
                void handleDesigSubmit((data) => createDesigMutation.mutate(data))(e);
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.titleEn", "Title (English)")} *
                </label>
                <Input
                  {...registerDesig("title")}
                  placeholder="e.g. Senior Teacher"
                  className="h-9 text-xs"
                />
                {desigErrors.title && (
                  <p className="mt-1 text-[11px] text-rose-600">{desigErrors.title.message}</p>
                )}
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.titleBn", "Title (Bangla)")}
                </label>
                <Input
                  {...registerDesig("title_bn")}
                  placeholder="যেমন: সিনিয়র শিক্ষক"
                  className="h-9 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("staff.desigCode", "Code")} *
                  </label>
                  <Input
                    {...registerDesig("code")}
                    placeholder="e.g. SNR_TCHR"
                    className="h-9 text-xs font-mono uppercase"
                  />
                  {desigErrors.code && (
                    <p className="mt-1 text-[11px] text-rose-600">{desigErrors.code.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("staff.rankOrder", "Rank Order")} *
                  </label>
                  <Input
                    type="number"
                    {...registerDesig("rank_order")}
                    className="h-9 text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.roleCategory", "Role Category")} *
                </label>
                <select
                  {...registerDesig("role_category")}
                  className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                >
                  <option value="teacher">Teacher</option>
                  <option value="admin">Administration</option>
                  <option value="support">Support</option>
                  <option value="driver">Driver</option>
                  <option value="security">Security</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDesigModal(false)}
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isDesigSubmitting || createDesigMutation.isPending}
                  className="bg-emerald-800 hover:bg-emerald-900 text-white"
                >
                  {isDesigSubmitting ? t("common.saving", "Saving...") : t("common.save", "Save")}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
