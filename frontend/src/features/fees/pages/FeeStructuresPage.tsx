import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Building2,
  DollarSign,
  Plus,
  Search,
  Tag,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { feesApi, type FeeHead, type FeeStructure } from "@/features/fees/api/feesApi";
import {
  feeHeadSchema,
  feeStructureSchema,
  feeStructureItemSchema,
  type FeeHeadFormData,
  type FeeStructureFormData,
  type FeeStructureItemFormData,
} from "@/features/fees/schemas/feeSchemas";
import { apiClient } from "@/lib/api-client";

export default function FeeStructuresPage() {
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState<"structures" | "heads">("structures");
  const [heads, setHeads] = useState<FeeHead[]>([]);
  const [structures, setStructures] = useState<FeeStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Academic sessions and classes for selection
  const [sessions, setSessions] = useState<Array<{ id: string; name: string }>>([]);
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);

  // Modals
  const [isHeadModalOpen, setIsHeadModalOpen] = useState(false);
  const [isStructureModalOpen, setIsStructureModalOpen] = useState(false);
  const [isItemModalOpen, setIsItemModalOpen] = useState(false);
  const [selectedStructureId, setSelectedStructureId] = useState<string | null>(null);

  // Forms
  const headForm = useForm<FeeHeadFormData>({
    resolver: zodResolver(feeHeadSchema),
    defaultValues: {
      code: "",
      name_en: "",
      name_bn: "",
      fee_type: "tuition",
      recurrence: "monthly",
      is_optional: false,
      is_refundable: false,
      is_active: true,
      description: "",
    },
  });

  const structureForm = useForm<FeeStructureFormData>({
    resolver: zodResolver(feeStructureSchema),
    defaultValues: {
      session: "",
      class_level: "",
      name: "",
      is_active: true,
    },
  });

  const itemForm = useForm<FeeStructureItemFormData>({
    resolver: zodResolver(feeStructureItemSchema),
    defaultValues: {
      fee_head: "",
      amount: "1000",
      due_day: 10,
      applicable_months: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [headsRes, structsRes, sessRes, classesRes] = await Promise.all([
        feesApi.getFeeHeads({ search: search || undefined }),
        feesApi.getFeeStructures(),
        apiClient.GET("/api/v1/institutions/sessions/"),
        apiClient.GET("/api/v1/academics/classes/"),
      ]);
      setHeads(((headsRes as { results?: FeeHead[] }).results ?? []));
      setStructures(((structsRes as { results?: FeeStructure[] }).results ?? []));

      if (sessRes.data && "results" in sessRes.data) {
        setSessions(sessRes.data.results);
      }
      if (classesRes.data && "results" in classesRes.data) {
        setClasses(classesRes.data.results);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const handleCreateHead = async (data: FeeHeadFormData) => {
    try {
      await feesApi.createFeeHead(data);
      setIsHeadModalOpen(false);
      headForm.reset();
      void fetchData();
    } catch {
      // error handled by api client
    }
  };

  const handleCreateStructure = async (data: FeeStructureFormData) => {
    try {
      await feesApi.createFeeStructure(data);
      setIsStructureModalOpen(false);
      structureForm.reset();
      void fetchData();
    } catch {
      // error handled
    }
  };

  const handleAddItem = async (data: FeeStructureItemFormData) => {
    if (!selectedStructureId) return;
    try {
      await feesApi.addStructureItem(selectedStructureId, {
        fee_head: data.fee_head,
        amount: data.amount,
        due_day: data.due_day,
        applicable_months: data.applicable_months,
      });
      setIsItemModalOpen(false);
      itemForm.reset();
      void fetchData();
    } catch {
      // error handled
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <DollarSign className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            {t("fees.structuresAndHeads", "Fee Structures & Heads")}
          </h1>
          <p className="text-sm text-slate-500">
            {t("fees.structuresSubtitle", "Configure academic fee categories, recurring rates, and class-wise fee schedules.")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeTab === "structures" ? (
            <Button onClick={() => setIsStructureModalOpen(true)} className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white">
              <Plus className="h-4 w-4" />
              {t("fees.createStructure", "New Fee Structure")}
            </Button>
          ) : (
            <Button onClick={() => setIsHeadModalOpen(true)} className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white">
              <Plus className="h-4 w-4" />
              {t("fees.createHead", "New Fee Head")}
            </Button>
          )}
        </div>
      </div>

      {/* Nav Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab("structures")}
          className={`pb-3 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "structures"
              ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <FileSpreadsheet className="h-4 w-4" />
          {t("fees.feeStructures", "Fee Structures")} ({structures.length})
        </button>
        <button
          onClick={() => setActiveTab("heads")}
          className={`pb-3 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "heads"
              ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Tag className="h-4 w-4" />
          {t("fees.feeHeads", "Fee Heads / Categories")} ({heads.length})
        </button>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("common.search", "Search...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-white dark:bg-slate-900"
          />
        </div>
      </div>

      {/* Tab 1: Fee Structures */}
      {activeTab === "structures" && (
        <div className="space-y-4">
          {loading ? (
            <div className="p-8 text-center text-slate-500">{t("common.loading", "Loading...")}</div>
          ) : structures.length === 0 ? (
            <div className="p-12 text-center border rounded-xl border-dashed border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <Building2 className="h-10 w-10 text-slate-300 mx-auto mb-2" />
              <p className="font-medium text-slate-600 dark:text-slate-300">{t("fees.noStructuresFound", "No fee structures configured yet.")}</p>
              <p className="text-xs text-slate-400 mt-1">{t("fees.createStructurePrompt", "Create class fee templates to automate monthly and term billing.")}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {structures.map((st) => {
                const totalAnnual = (st.items || []).reduce((acc, curr) => acc + Number(curr.amount || 0), 0);
                return (
                  <div
                    key={st.id}
                    className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow"
                  >
                    <div>
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-base">{st.name}</h3>
                          <span className="text-xs text-slate-500 block">
                            {st.class_level_name} | {st.session_name}
                          </span>
                        </div>
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                            st.is_active
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                          }`}
                        >
                          {st.is_active ? t("common.active", "Active") : t("common.inactive", "Inactive")}
                        </span>
                      </div>

                      {/* Items List */}
                      <div className="mt-4 border-t border-slate-100 dark:border-slate-800 pt-3 space-y-1.5">
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          {t("fees.lineItems", "Line Items")} ({st.items?.length || 0})
                        </div>
                        {(st.items || []).length === 0 ? (
                          <p className="text-xs text-slate-400 italic">{t("fees.noItemsAdded", "No line items added yet.")}</p>
                        ) : (
                          st.items.map((it) => (
                            <div key={it.id} className="flex justify-between items-center text-xs py-0.5">
                              <span className="text-slate-700 dark:text-slate-300 font-medium">{it.fee_head_name}</span>
                              <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                                ৳{Number(it.amount).toFixed(2)}
                              </span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                      <div className="text-xs">
                        <span className="text-slate-400 block">{t("fees.totalAmount", "Total Base")}</span>
                        <span className="text-sm font-bold font-mono text-emerald-600 dark:text-emerald-400">
                          ৳{totalAnnual.toFixed(2)}
                        </span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedStructureId(st.id);
                          setIsItemModalOpen(true);
                        }}
                        className="text-xs h-8"
                      >
                        <Plus className="h-3.5 w-3.5 mr-1" />
                        {t("fees.addItem", "Add Item")}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Fee Heads */}
      {activeTab === "heads" && (
        <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
                <tr>
                  <th className="py-3 px-4">{t("fees.code", "Code")}</th>
                  <th className="py-3 px-4">{t("fees.nameEn", "Head Name (EN)")}</th>
                  <th className="py-3 px-4">{t("fees.nameBn", "Head Name (BN)")}</th>
                  <th className="py-3 px-4">{t("fees.type", "Category")}</th>
                  <th className="py-3 px-4">{t("fees.recurrence", "Recurrence")}</th>
                  <th className="py-3 px-4 text-center">{t("fees.optional", "Optional")}</th>
                  <th className="py-3 px-4 text-center">{t("common.status", "Status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {heads.map((h) => (
                  <tr key={h.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-slate-900 dark:text-slate-100">{h.code}</td>
                    <td className="py-3 px-4 font-semibold text-slate-800 dark:text-slate-200">{h.name_en}</td>
                    <td className="py-3 px-4 font-bengali text-slate-600 dark:text-slate-400">{h.name_bn || "—"}</td>
                    <td className="py-3 px-4 uppercase text-xs font-semibold text-slate-500">{h.fee_type}</td>
                    <td className="py-3 px-4 capitalize text-xs">{h.recurrence.replace("_", " ")}</td>
                    <td className="py-3 px-4 text-center">
                      {h.is_optional ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 inline" />
                      ) : (
                        <XCircle className="h-4 w-4 text-slate-300 dark:text-slate-600 inline" />
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                          h.is_active
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        }`}
                      >
                        {h.is_active ? t("common.active", "Active") : t("common.inactive", "Inactive")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal 1: Create Fee Head */}
      <Dialog open={isHeadModalOpen} onOpenChange={setIsHeadModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("fees.createHead", "Create Fee Head")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { void headForm.handleSubmit(handleCreateHead)(e); }} className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("fees.code", "Code")}</FormLabel>
                <Input {...headForm.register("code")} placeholder="e.g. TUITION" className="uppercase" />
                <FormMessage>{headForm.formState.errors.code?.message}</FormMessage>
              </FormField>
              <FormField>
                <FormLabel>{t("fees.category", "Category")}</FormLabel>
                <select
                  {...headForm.register("fee_type")}
                  className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                >
                  <option value="tuition">Tuition</option>
                  <option value="exam">Exam</option>
                  <option value="admission">Admission</option>
                  <option value="session">Session</option>
                  <option value="transport">Transport</option>
                  <option value="lab">Lab</option>
                  <option value="library">Library</option>
                  <option value="other">Other</option>
                </select>
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("fees.nameEn", "Name (English)")}</FormLabel>
              <Input {...headForm.register("name_en")} placeholder="e.g. Monthly Tuition Fee" />
              <FormMessage>{headForm.formState.errors.name_en?.message}</FormMessage>
            </FormField>

            <FormField>
              <FormLabel>{t("fees.nameBn", "Name (Bangla)")}</FormLabel>
              <Input {...headForm.register("name_bn")} placeholder="যেমন: মাসিক বেতন" />
              <FormMessage>{headForm.formState.errors.name_bn?.message}</FormMessage>
            </FormField>

            <FormField>
              <FormLabel>{t("fees.recurrence", "Recurrence")}</FormLabel>
              <select
                {...headForm.register("recurrence")}
                className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
              >
                <option value="monthly">Monthly</option>
                <option value="term">Term / Semester</option>
                <option value="annual">Annual</option>
                <option value="one_time">One Time</option>
              </select>
            </FormField>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsHeadModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {t("common.save", "Save Fee Head")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 2: Create Fee Structure */}
      <Dialog open={isStructureModalOpen} onOpenChange={setIsStructureModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("fees.createStructure", "Create Fee Structure")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { void structureForm.handleSubmit(handleCreateStructure)(e); }} className="space-y-4 py-2">
            <FormField>
              <FormLabel>{t("fees.structureName", "Structure Name")}</FormLabel>
              <Input {...structureForm.register("name")} placeholder="e.g. Class 10 General Fee 2026" />
              <FormMessage>{structureForm.formState.errors.name?.message}</FormMessage>
            </FormField>

            <FormField>
              <FormLabel>{t("academics.academicSession", "Academic Session")}</FormLabel>
              <select
                {...structureForm.register("session")}
                className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
              >
                <option value="">{t("common.select", "Select Session...")}</option>
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <FormMessage>{structureForm.formState.errors.session?.message}</FormMessage>
            </FormField>

            <FormField>
              <FormLabel>{t("academics.class", "Class")}</FormLabel>
              <select
                {...structureForm.register("class_level")}
                className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
              >
                <option value="">{t("common.select", "Select Class...")}</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <FormMessage>{structureForm.formState.errors.class_level?.message}</FormMessage>
            </FormField>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsStructureModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {t("common.create", "Create Structure")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 3: Add Structure Item */}
      <Dialog open={isItemModalOpen} onOpenChange={setIsItemModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("fees.addItem", "Add Line Item to Structure")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { void itemForm.handleSubmit(handleAddItem)(e); }} className="space-y-4 py-2">
            <FormField>
              <FormLabel>{t("fees.feeHead", "Fee Head")}</FormLabel>
              <select
                {...itemForm.register("fee_head")}
                className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
              >
                <option value="">{t("common.select", "Select Fee Head...")}</option>
                {heads.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name_en} ({h.code})
                  </option>
                ))}
              </select>
              <FormMessage>{itemForm.formState.errors.fee_head?.message}</FormMessage>
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("common.amount", "Amount (৳)")}</FormLabel>
                <Input {...itemForm.register("amount")} type="number" step="0.01" />
                <FormMessage>{itemForm.formState.errors.amount?.message}</FormMessage>
              </FormField>
              <FormField>
                <FormLabel>{t("fees.dueDayOfMonth", "Due Day of Month")}</FormLabel>
                <Input {...itemForm.register("due_day", { valueAsNumber: true })} type="number" min={1} max={31} />
                <FormMessage>{itemForm.formState.errors.due_day?.message}</FormMessage>
              </FormField>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsItemModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {t("common.add", "Add Item")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
