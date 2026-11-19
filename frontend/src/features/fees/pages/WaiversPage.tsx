import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Award,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
  ShieldCheck,
  Tag,
  UserCheck,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel } from "@/components/ui/form";
import { feesApi, type WaiverRuleItem, type StudentWaiverItem } from "@/features/fees/api/feesApi";
import { apiClient } from "@/lib/api-client";

export default function WaiversPage() {
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState<"allocations" | "rules">("allocations");
  const [waiverRules, setWaiverRules] = useState<WaiverRuleItem[]>([]);
  const [studentWaivers, setStudentWaivers] = useState<StudentWaiverItem[]>([]);
  const [loading, setLoading] = useState(true);

  // New Rule Modal
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [ruleName, setRuleName] = useState("");
  const [ruleCategory, setRuleCategory] = useState<WaiverRuleItem["category"]>("merit");
  const [discountType, setDiscountType] = useState<"percentage" | "fixed_amount">("percentage");
  const [discountValue, setDiscountValue] = useState("50");
  const [ruleDesc, setRuleDesc] = useState("");
  const [submittingRule, setSubmittingRule] = useState(false);

  // Assign Student Waiver Modal state
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [assignStudentSearch, setAssignStudentSearch] = useState("");
  const [studentOptions, setStudentOptions] = useState<Array<{ id: string; student_id: string; name_en: string; class_name?: string }>>([]);
  const [selectedStudent, setSelectedStudent] = useState<{ id: string; student_id: string; name_en: string; class_name?: string } | null>(null);
  const [selectedRuleId, setSelectedRuleId] = useState<string>("");
  const [waiverTitle, setWaiverTitle] = useState("");
  const [assignDiscountType, setAssignDiscountType] = useState<"percentage" | "flat">("percentage");
  const [assignDiscountValue, setAssignDiscountValue] = useState("50");
  const [validFrom, setValidFrom] = useState(new Date().toISOString().slice(0, 10));
  const [validTo, setValidTo] = useState(new Date(new Date().getFullYear(), 11, 31).toISOString().slice(0, 10));
  const [submittingAssign, setSubmittingAssign] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [rulesRes, studentRes] = await Promise.all([
        feesApi.getWaiverRules(),
        feesApi.getStudentWaivers(),
      ]);
      setWaiverRules(((rulesRes as { results?: WaiverRuleItem[] }).results ?? []));
      setStudentWaivers(((studentRes as { results?: StudentWaiverItem[] }).results ?? []));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleName.trim()) return;
    setSubmittingRule(true);
    try {
      await feesApi.createWaiverRule({
        name: ruleName,
        category: ruleCategory,
        discount_type: discountType,
        discount_value: discountValue,
        description: ruleDesc,
        is_active: true,
      });
      setIsRuleModalOpen(false);
      setRuleName("");
      void fetchData();
    } catch {
      // ignore
    } finally {
      setSubmittingRule(false);
    }
  };

  const handleSearchStudents = useCallback(async (query: string) => {
    setAssignStudentSearch(query);
    if (!query || query.length < 2) {
      setStudentOptions([]);
      return;
    }
    try {
      const res = await apiClient.GET("/api/v1/students/", {
        params: { query: { search: query } as never },
      });
      if (res.data && "results" in res.data) {
        setStudentOptions(
          (res.data.results as Array<{ id: string; student_id: string; name_en: string; class_name?: string }>).slice(0, 8)
        );
      }
    } catch {
      // ignore
    }
  }, []);

  const handleSelectRule = (ruleId: string) => {
    setSelectedRuleId(ruleId);
    const rule = waiverRules.find((r) => r.id === ruleId);
    if (rule) {
      setWaiverTitle(rule.name);
      setAssignDiscountType(rule.discount_type === "percentage" ? "percentage" : "flat");
      setAssignDiscountValue(String(rule.discount_value));
    }
  };

  const handleAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStudent) {
      setAssignError("Please search and select a student");
      return;
    }
    setSubmittingAssign(true);
    setAssignError(null);
    try {
      await feesApi.createStudentWaiver({
        student: selectedStudent.id,
        waiver_rule: selectedRuleId || null,
        title: waiverTitle || (selectedRuleId ? waiverRules.find((r) => r.id === selectedRuleId)?.name : "Student Concession"),
        discount_type: assignDiscountType,
        discount_value: assignDiscountValue,
        valid_from: validFrom || null,
        valid_to: validTo || null,
      });
      setIsAssignModalOpen(false);
      setSelectedStudent(null);
      setAssignStudentSearch("");
      setSelectedRuleId("");
      void fetchData();
    } catch (err: unknown) {
      setAssignError(err instanceof Error ? err.message : "Failed to assign student waiver");
    } finally {
      setSubmittingAssign(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await feesApi.approveStudentWaiver(id);
      void fetchData();
    } catch {
      // ignore
    }
  };

  const handleReject = async (id: string) => {
    try {
      await feesApi.rejectStudentWaiver(id, "Rejected by administration");
      void fetchData();
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Award className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            {t("fees.waiversAndScholarships", "Waivers & Scholarships")}
          </h1>
          <p className="text-sm text-slate-500">
            {t("fees.waiversSubtitle", "Manage institutional scholarship criteria, sibling discounts, and student concession approvals.")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={() => setIsAssignModalOpen(true)}
            className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            <UserCheck className="h-4 w-4" />
            {t("fees.assignStudentWaiver", "Assign Student Waiver")}
          </Button>
          <Button
            onClick={() => setIsRuleModalOpen(true)}
            variant="outline"
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            {t("fees.createWaiverRule", "New Waiver Policy")}
          </Button>
        </div>
      </div>

      {/* Nav Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab("allocations")}
          className={`pb-3 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "allocations"
              ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          {t("fees.studentWaiverRequests", "Student Concessions")} ({studentWaivers.length})
        </button>
        <button
          onClick={() => setActiveTab("rules")}
          className={`pb-3 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "rules"
              ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Tag className="h-4 w-4" />
          {t("fees.waiverPolicies", "Institutional Policies")} ({waiverRules.length})
        </button>
      </div>

      {/* Tab 1: Student Waiver Allocations */}
      {activeTab === "allocations" && (
        <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
                <tr>
                  <th className="py-3 px-4">{t("students.student", "Student Name")}</th>
                  <th className="py-3 px-4">{t("fees.waiverTitle", "Concession Title")}</th>
                  <th className="py-3 px-4">{t("fees.discountValue", "Benefit")}</th>
                  <th className="py-3 px-4">{t("fees.validity", "Validity Period")}</th>
                  <th className="py-3 px-4 text-center">{t("common.status", "Status")}</th>
                  <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      {t("common.loading", "Loading student waivers...")}
                    </td>
                  </tr>
                ) : studentWaivers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-500">
                      <Award className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                      <p className="text-sm font-medium">{t("fees.noWaiversFound", "No student waiver concessions registered.")}</p>
                      <Button
                        size="sm"
                        onClick={() => setIsAssignModalOpen(true)}
                        className="mt-3 gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                      >
                        <UserCheck className="h-3.5 w-3.5" />
                        {t("fees.assignStudentWaiver", "Assign Student Waiver")}
                      </Button>
                    </td>
                  </tr>
                ) : (
                  studentWaivers.map((sw) => (
                    <tr key={sw.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 px-4">
                        <span className="font-semibold text-slate-800 dark:text-slate-200 block">{sw.student_name}</span>
                        <span className="font-mono text-xs text-slate-400">{sw.student_code}</span>
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100">
                        {sw.title || sw.waiver_rule_name}
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        {sw.discount_type === "percentage" ? `${Number(sw.discount_value)}%` : `৳${Number(sw.discount_value).toFixed(2)}`}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-500">
                        {sw.valid_from} to {sw.valid_to}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`text-[11px] px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider inline-flex items-center gap-1 ${
                            sw.status === "approved"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400"
                              : sw.status === "rejected"
                              ? "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-400"
                              : "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400"
                          }`}
                        >
                          {sw.status === "approved" && <CheckCircle className="h-3 w-3" />}
                          {sw.status === "rejected" && <XCircle className="h-3 w-3" />}
                          {sw.status === "pending" && <Clock className="h-3 w-3" />}
                          {sw.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {sw.status === "pending" ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => { void handleApprove(sw.id); }}
                              className="h-8 text-xs text-emerald-600 hover:text-emerald-700"
                            >
                              {t("common.approve", "Approve")}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => { void handleReject(sw.id); }}
                              className="h-8 text-xs text-rose-600 hover:text-rose-700"
                            >
                              {t("common.reject", "Reject")}
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">
                            {sw.approved_by_name ? `By ${sw.approved_by_name}` : "—"}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Waiver Policies */}
      {activeTab === "rules" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {waiverRules.map((rule) => (
            <div
              key={rule.id}
              className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-base">{rule.name}</h3>
                    <span className="text-xs font-semibold uppercase text-emerald-600 dark:text-emerald-400 block mt-0.5">
                      {rule.category.replace("_", " ")}
                    </span>
                  </div>
                  <span className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
                    {rule.discount_type === "percentage" ? `${Number(rule.discount_value)}% OFF` : `৳${Number(rule.discount_value).toFixed(2)}`}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-2">{rule.description || t("fees.noPolicyDesc", "Standard institutional fee waiver policy.")}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-xs text-slate-400">
                <span>{t("common.status", "Status")}</span>
                <span className="font-semibold text-emerald-600">{rule.is_active ? "Active Policy" : "Inactive"}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal: Create Waiver Policy */}
      <Dialog open={isRuleModalOpen} onOpenChange={setIsRuleModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("fees.createWaiverRule", "Create Waiver Policy")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { void handleCreateRule(e); }} className="space-y-4 py-2">
            <FormField>
              <FormLabel>{t("fees.policyName", "Policy Name")}</FormLabel>
              <Input
                placeholder="e.g. Sibling Concession 50%"
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                required
              />
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("fees.category", "Category")}</FormLabel>
                <select
                  value={ruleCategory}
                  onChange={(e) => setRuleCategory(e.target.value as WaiverRuleItem["category"])}
                  className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                >
                  <option value="merit">Merit Scholarship</option>
                  <option value="sibling">Sibling Discount</option>
                  <option value="freedom_fighter">Freedom Fighter Quota</option>
                  <option value="poor_fund">Poor Fund / Orphan</option>
                  <option value="staff_child">Staff Child Concession</option>
                  <option value="special">Special Concession</option>
                </select>
              </FormField>

              <FormField>
                <FormLabel>{t("fees.discountType", "Discount Type")}</FormLabel>
                <select
                  value={discountType}
                  onChange={(e) => setDiscountType(e.target.value as "percentage" | "fixed_amount")}
                  className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                >
                  <option value="percentage">Percentage (%)</option>
                  <option value="fixed_amount">Fixed BDT (৳)</option>
                </select>
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("fees.discountValue", "Discount Value")}</FormLabel>
              <Input
                type="number"
                step="0.01"
                value={discountValue}
                onChange={(e) => setDiscountValue(e.target.value)}
                required
              />
            </FormField>

            <FormField>
              <FormLabel>{t("common.description", "Description")}</FormLabel>
              <Input
                placeholder="e.g. Applicable for second sibling enrolled in the school"
                value={ruleDesc}
                onChange={(e) => setRuleDesc(e.target.value)}
              />
            </FormField>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsRuleModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" disabled={submittingRule} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {submittingRule ? t("common.saving", "Saving...") : t("common.create", "Create Policy")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal: Assign Student Waiver */}
      <Dialog open={isAssignModalOpen} onOpenChange={setIsAssignModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("fees.assignStudentWaiver", "Assign Student Waiver")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { void handleAssignSubmit(e); }} className="space-y-4 py-2">
            {assignError && (
              <div className="p-3 text-xs bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 rounded-md border border-rose-200 dark:border-rose-900">
                {assignError}
              </div>
            )}

            {/* Student Search & Select */}
            <FormField>
              <FormLabel>{t("students.student", "Student")}</FormLabel>
              {selectedStudent ? (
                <div className="flex items-center justify-between p-2.5 rounded-lg border border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30">
                  <div>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm block">
                      {selectedStudent.name_en}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      {selectedStudent.student_id} {selectedStudent.class_name ? `• ${selectedStudent.class_name}` : ""}
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedStudent(null);
                      setAssignStudentSearch("");
                    }}
                    className="h-7 text-xs text-slate-500 hover:text-rose-600"
                  >
                    {t("common.change", "Change")}
                  </Button>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <Input
                      placeholder="Type student name or ID (e.g. STU-1001)..."
                      value={assignStudentSearch}
                      onChange={(e) => { void handleSearchStudents(e.target.value); }}
                      className="pl-9"
                    />
                  </div>
                  {studentOptions.length > 0 && (
                    <div className="border border-slate-200 dark:border-slate-800 rounded-lg max-h-40 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900 shadow-md">
                      {studentOptions.map((st) => (
                        <button
                          key={st.id}
                          type="button"
                          onClick={() => {
                            setSelectedStudent(st);
                            setStudentOptions([]);
                            setAssignError(null);
                          }}
                          className="w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-800 flex justify-between items-center transition-colors"
                        >
                          <div>
                            <span className="font-semibold text-slate-900 dark:text-slate-100 block">
                              {st.name_en}
                            </span>
                            <span className="text-[11px] text-slate-400 font-mono">
                              {st.student_id}
                            </span>
                          </div>
                          {st.class_name && (
                            <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                              {st.class_name}
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </FormField>

            {/* Select Waiver Policy */}
            <FormField>
              <FormLabel>{t("fees.waiverPolicy", "Waiver Policy")}</FormLabel>
              <select
                value={selectedRuleId}
                onChange={(e) => handleSelectRule(e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
              >
                <option value="">-- Custom Concession (No preset policy) --</option>
                {waiverRules.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.discount_type === "percentage" ? `${Number(r.discount_value)}%` : `৳${Number(r.discount_value)}`})
                  </option>
                ))}
              </select>
            </FormField>

            {/* Concession Title */}
            <FormField>
              <FormLabel>{t("fees.waiverTitle", "Concession Title")}</FormLabel>
              <Input
                placeholder="e.g. Sibling Discount / Merit Scholarship"
                value={waiverTitle}
                onChange={(e) => setWaiverTitle(e.target.value)}
                required
              />
            </FormField>

            {/* Benefit Type & Amount */}
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("fees.discountType", "Benefit Type")}</FormLabel>
                <select
                  value={assignDiscountType}
                  onChange={(e) => setAssignDiscountType(e.target.value as "percentage" | "flat")}
                  className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                >
                  <option value="percentage">Percentage (%)</option>
                  <option value="flat">Fixed Amount (৳)</option>
                </select>
              </FormField>

              <FormField>
                <FormLabel>{t("fees.discountValue", "Benefit Amount")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  value={assignDiscountValue}
                  onChange={(e) => setAssignDiscountValue(e.target.value)}
                  required
                />
              </FormField>
            </div>

            {/* Validity Dates */}
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("fees.validFrom", "Valid From")}</FormLabel>
                <Input
                  type="date"
                  value={validFrom}
                  onChange={(e) => setValidFrom(e.target.value)}
                />
              </FormField>

              <FormField>
                <FormLabel>{t("fees.validTo", "Valid To")}</FormLabel>
                <Input
                  type="date"
                  value={validTo}
                  onChange={(e) => setValidTo(e.target.value)}
                />
              </FormField>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsAssignModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" disabled={submittingAssign} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {submittingAssign ? t("common.saving", "Saving...") : t("fees.submitConcession", "Save Concession")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
