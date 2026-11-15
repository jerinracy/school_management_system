import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Layers,
  Plus,
  Search,
  Sparkles,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
  Percent,
  DollarSign,
  Tag,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  payrollApi,
  type SalaryComponent,
  type SalaryStructure,
} from "@/features/payroll/api/payrollApi";

const componentFormSchema = z.object({
  code: z.string().min(2, "Code must be at least 2 characters").max(40),
  name_en: z.string().min(2, "English name is required").max(150),
  name_bn: z.string().optional(),
  component_type: z.enum(["earning", "deduction"]),
  calculation_type: z.enum(["fixed", "percentage_of_basic", "percentage_of_gross"]),
  default_value: z.number().min(0, "Default value must be non-negative"),
  is_taxable: z.boolean(),
  is_active: z.boolean(),
  display_order: z.number().int().min(0),
});

type ComponentFormData = z.infer<typeof componentFormSchema>;

const structureFormSchema = z.object({
  code: z.string().min(2, "Code is required").max(40),
  name: z.string().min(2, "Name is required").max(150),
  name_bn: z.string().optional(),
  description: z.string().optional(),
  is_active: z.boolean(),
});

type StructureFormData = z.infer<typeof structureFormSchema>;

export default function SalaryStructuresPage() {
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState<"structures" | "components">("structures");
  const [components, setComponents] = useState<SalaryComponent[]>([]);
  const [structures, setStructures] = useState<SalaryStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [isSeeding, setIsSeeding] = useState(false);

  // Modals
  const [isCompModalOpen, setIsCompModalOpen] = useState(false);
  const [isStructModalOpen, setIsStructModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Forms
  const compForm = useForm<ComponentFormData>({
    resolver: zodResolver(componentFormSchema),
    defaultValues: {
      code: "",
      name_en: "",
      name_bn: "",
      component_type: "earning",
      calculation_type: "fixed",
      default_value: 0,
      is_taxable: true,
      is_active: true,
      display_order: 10,
    },
  });

  const structForm = useForm<StructureFormData>({
    resolver: zodResolver(structureFormSchema),
    defaultValues: {
      code: "",
      name: "",
      name_bn: "",
      description: "",
      is_active: true,
    },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [compRes, structRes] = await Promise.all([
        payrollApi.getComponents(),
        payrollApi.getStructures(),
      ]);
      setComponents(compRes.results || []);
      setStructures(structRes.results || []);
    } catch {
      setNotification({ type: "error", message: t("payroll.loadFailed", "Failed to load salary configuration.") });
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  // Seed Default Components
  const handleSeedComponents = async () => {
    setIsSeeding(true);
    try {
      await payrollApi.seedDefaultComponents();
      setNotification({ type: "success", message: t("payroll.seedSuccess", "Standard Bangladeshi salary components seeded successfully.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.seedFailed", "Failed to seed default salary components.") });
    } finally {
      setIsSeeding(false);
    }
  };

  // Seed Default Structures
  const handleSeedStructures = async () => {
    setIsSeeding(true);
    try {
      await payrollApi.seedDefaultStructures();
      setNotification({ type: "success", message: t("payroll.seedStructSuccess", "Standard school salary structures seeded successfully.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.seedStructFailed", "Failed to seed default salary structures.") });
    } finally {
      setIsSeeding(false);
    }
  };

  // Create Component Submit
  const handleCompSubmit = async (data: ComponentFormData) => {
    try {
      await payrollApi.createComponent({
        ...data,
        default_value: data.default_value.toString(),
      });
      setIsCompModalOpen(false);
      compForm.reset();
      setNotification({ type: "success", message: t("payroll.compCreated", "Salary component created successfully.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.compCreateFailed", "Failed to create salary component.") });
    }
  };

  // Create Structure Submit
  const handleStructSubmit = async (data: StructureFormData) => {
    try {
      await payrollApi.createStructure(data);
      setIsStructModalOpen(false);
      structForm.reset();
      setNotification({ type: "success", message: t("payroll.structCreated", "Salary structure created successfully.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.structCreateFailed", "Failed to create salary structure.") });
    }
  };

  const filteredComponents = components.filter(
    (c) =>
      c.code.toLowerCase().includes(search.toLowerCase()) ||
      c.name_en.toLowerCase().includes(search.toLowerCase()) ||
      (c.name_bn && c.name_bn.includes(search))
  );

  const filteredStructures = structures.filter(
    (s) =>
      s.code.toLowerCase().includes(search.toLowerCase()) ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.name_bn && s.name_bn.includes(search))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Layers className="h-6 w-6 text-emerald-600" />
            {t("payroll.structuresTitle", "Salary Structures & Components")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t("payroll.structuresSubtitle", "Configure institutional grade structures, allowances, bonuses, and standard deductions.")}
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {activeTab === "structures" ? (
            <>
              <Button
                variant="outline"
                onClick={() => { void handleSeedStructures(); }}
                disabled={isSeeding}
                className="gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
              >
                <Sparkles className="h-4 w-4" />
                {t("payroll.seedDefaultStructures", "Seed Standard Structures")}
              </Button>
              <Button onClick={() => setIsStructModalOpen(true)} className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white">
                <Plus className="h-4 w-4" />
                {t("payroll.addStructure", "Add Structure Template")}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => { void handleSeedComponents(); }}
                disabled={isSeeding}
                className="gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
              >
                <Sparkles className="h-4 w-4" />
                {t("payroll.seedDefaultComponents", "Seed Standard Components")}
              </Button>
              <Button onClick={() => setIsCompModalOpen(true)} className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white">
                <Plus className="h-4 w-4" />
                {t("payroll.addComponent", "Add Component")}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          role="alert"
          className={`p-3 rounded-lg flex items-center justify-between text-sm ${
            notification.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "bg-rose-50 text-rose-800 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300"
          }`}
        >
          <span>{notification.message}</span>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-600 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <button
          type="button"
          onClick={() => setActiveTab("structures")}
          className={`py-2 px-4 border-b-2 font-medium text-sm flex items-center gap-2 ${
            activeTab === "structures"
              ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          }`}
        >
          <FileSpreadsheet className="h-4 w-4" />
          {t("payroll.structuresTab", "Salary Structure Templates")} ({structures.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("components")}
          className={`py-2 px-4 border-b-2 font-medium text-sm flex items-center gap-2 ${
            activeTab === "components"
              ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          }`}
        >
          <Tag className="h-4 w-4" />
          {t("payroll.componentsTab", "Earnings & Deductions Components")} ({components.length})
        </button>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <Input
          placeholder={t("common.search", "Search by code, title, or Bangla name...")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Tab 1: Structures */}
      {activeTab === "structures" && (
        <div className="space-y-4">
          {loading ? (
            <div className="text-center py-12 text-slate-500">{t("common.loading", "Loading templates...")}</div>
          ) : filteredStructures.length === 0 ? (
            <div className="text-center py-12 border rounded-xl bg-slate-50 dark:bg-slate-900/50">
              <FileSpreadsheet className="h-10 w-10 text-slate-400 mx-auto mb-2" />
              <p className="font-semibold text-slate-700 dark:text-slate-300">
                {t("payroll.noStructuresFound", "No salary structures configured yet.")}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {t("payroll.seedOrAddPrompt", "Click 'Seed Standard Structures' to populate standard Bangladeshi school grades (Senior Teacher, Office Staff, etc.).")}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredStructures.map((struct) => (
                <div
                  key={struct.id}
                  className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm space-y-3 hover:border-emerald-200 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold">
                          {struct.code}
                        </span>
                        <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                          {struct.name}
                        </h3>
                      </div>
                      {struct.name_bn && (
                        <p className="text-xs text-slate-500 mt-0.5">{struct.name_bn}</p>
                      )}
                    </div>
                    {struct.is_active ? (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                        <CheckCircle2 className="h-3 w-3" />
                        {t("common.active", "Active")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                        <XCircle className="h-3 w-3" />
                        {t("common.inactive", "Inactive")}
                      </span>
                    )}
                  </div>

                  {struct.description && (
                    <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
                      {struct.description}
                    </p>
                  )}

                  {/* Components summary table */}
                  <div className="border rounded-lg overflow-hidden text-xs">
                    <div className="bg-slate-50 dark:bg-slate-800 px-3 py-1.5 font-semibold text-slate-600 dark:text-slate-300 flex justify-between">
                      <span>{t("payroll.component", "Component")}</span>
                      <span>{t("payroll.rule", "Calculation Rule")}</span>
                    </div>
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      {struct.lines && struct.lines.length > 0 ? (
                        struct.lines.map((line) => (
                          <div key={line.id} className="px-3 py-1.5 flex justify-between items-center">
                            <span className="text-slate-700 dark:text-slate-300 font-medium">
                              {line.component_name_en}
                            </span>
                            <span className="font-mono text-slate-600 dark:text-slate-400">
                              {line.calculation_type === "percentage_of_basic"
                                ? `${line.value}% Basic`
                                : line.calculation_type === "percentage_of_gross"
                                ? `${line.value}% Gross`
                                : `৳${line.value}`}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div className="px-3 py-2 text-slate-400 text-center italic">
                          {t("payroll.noComponentsAssigned", "No components assigned.")}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Components */}
      {activeTab === "components" && (
        <div className="border rounded-xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/60 border-b text-xs font-semibold uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="py-3 px-4">{t("common.code", "Code")}</th>
                  <th className="py-3 px-4">{t("common.name", "Name (English / বাংলা)")}</th>
                  <th className="py-3 px-4">{t("payroll.type", "Type")}</th>
                  <th className="py-3 px-4">{t("payroll.calculation", "Calculation Rule")}</th>
                  <th className="py-3 px-4">{t("payroll.defaultValue", "Default Value")}</th>
                  <th className="py-3 px-4">{t("payroll.taxable", "Taxable")}</th>
                  <th className="py-3 px-4">{t("common.status", "Status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      {t("common.loading", "Loading components...")}
                    </td>
                  </tr>
                ) : filteredComponents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      {t("payroll.noComponentsFound", "No components found.")}
                    </td>
                  </tr>
                ) : (
                  filteredComponents.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-4 font-mono font-semibold text-xs text-slate-700 dark:text-slate-300">
                        {c.code}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-900 dark:text-slate-100">{c.name_en}</div>
                        {c.name_bn && <div className="text-xs text-slate-500">{c.name_bn}</div>}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                            c.component_type === "earning"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                              : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                          }`}
                        >
                          {c.component_type === "earning"
                            ? t("payroll.earning", "Earning")
                            : t("payroll.deduction", "Deduction")}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-xs font-medium text-slate-600 dark:text-slate-300">
                        {c.calculation_type === "percentage_of_basic" ? (
                          <span className="flex items-center gap-1">
                            <Percent className="h-3 w-3 text-emerald-600" /> % of Basic
                          </span>
                        ) : c.calculation_type === "percentage_of_gross" ? (
                          <span className="flex items-center gap-1">
                            <Percent className="h-3 w-3 text-blue-600" /> % of Gross
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <DollarSign className="h-3 w-3 text-slate-600" /> Fixed Amount
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-xs">
                        {c.calculation_type.startsWith("percentage")
                          ? `${c.default_value}%`
                          : `৳${Number(c.default_value).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
                      </td>
                      <td className="py-3 px-4 text-xs">
                        {c.is_taxable ? (
                          <span className="text-emerald-700 dark:text-emerald-400 font-medium">Yes</span>
                        ) : (
                          <span className="text-slate-400">Exempt</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {c.is_active ? (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                            <CheckCircle2 className="h-3 w-3" />
                            {t("common.active", "Active")}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                            <XCircle className="h-3 w-3" />
                            {t("common.inactive", "Inactive")}
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

      {/* Modal 1: Add Component */}
      <Dialog open={isCompModalOpen} onOpenChange={setIsCompModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.createComponentTitle", "Create Salary Component")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void compForm.handleSubmit(handleCompSubmit)(e);
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("common.code", "Code")}</FormLabel>
                <Input placeholder="e.g. HRA, MED, PF" {...compForm.register("code")} />
                {compForm.formState.errors.code && (
                  <FormMessage>{compForm.formState.errors.code.message}</FormMessage>
                )}
              </FormField>
              <FormField>
                <FormLabel>{t("payroll.type", "Type")}</FormLabel>
                <select
                  {...compForm.register("component_type")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  <option value="earning">{t("payroll.earning", "Earning")}</option>
                  <option value="deduction">{t("payroll.deduction", "Deduction")}</option>
                </select>
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.nameEn", "Name (English)")}</FormLabel>
              <Input placeholder="e.g. House Rent Allowance" {...compForm.register("name_en")} />
              {compForm.formState.errors.name_en && (
                <FormMessage>{compForm.formState.errors.name_en.message}</FormMessage>
              )}
            </FormField>

            <FormField>
              <FormLabel>{t("payroll.nameBn", "Name (Bangla)")}</FormLabel>
              <Input placeholder="e.g. বাড়ি ভাড়া ভাতা" {...compForm.register("name_bn")} />
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.calculationType", "Calculation Rule")}</FormLabel>
                <select
                  {...compForm.register("calculation_type")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  <option value="fixed">Fixed BDT Amount</option>
                  <option value="percentage_of_basic">% of Basic Salary</option>
                  <option value="percentage_of_gross">% of Gross Salary</option>
                </select>
              </FormField>
              <FormField>
                <FormLabel>{t("payroll.defaultValue", "Default Value")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  {...compForm.register("default_value", { valueAsNumber: true })}
                />
              </FormField>
            </div>

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsCompModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("common.save", "Save Component")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 2: Add Structure */}
      <Dialog open={isStructModalOpen} onOpenChange={setIsStructModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.createStructureTitle", "Create Salary Structure Template")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void structForm.handleSubmit(handleStructSubmit)(e);
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("common.code", "Code")}</FormLabel>
                <Input placeholder="e.g. SNR-TCHR" {...structForm.register("code")} />
                {structForm.formState.errors.code && (
                  <FormMessage>{structForm.formState.errors.code.message}</FormMessage>
                )}
              </FormField>
              <FormField>
                <FormLabel>{t("common.name", "Template Name")}</FormLabel>
                <Input placeholder="e.g. Senior Teacher Grade" {...structForm.register("name")} />
                {structForm.formState.errors.name && (
                  <FormMessage>{structForm.formState.errors.name.message}</FormMessage>
                )}
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.nameBn", "Name (Bangla)")}</FormLabel>
              <Input placeholder="e.g. জ্যেষ্ঠ শিক্ষক স্কেল" {...structForm.register("name_bn")} />
            </FormField>

            <FormField>
              <FormLabel>{t("common.description", "Description")}</FormLabel>
              <Input placeholder="Structure notes..." {...structForm.register("description")} />
            </FormField>

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsStructModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("common.save", "Create Structure")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
