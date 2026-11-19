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
  Pencil,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  payrollApi,
  type CalculationType,
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

interface DeleteTarget {
  type: "structure" | "component" | "line";
  id: string;
  name: string;
  structureId?: string;
}

export default function SalaryStructuresPage() {
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState<"structures" | "components">("structures");
  const [components, setComponents] = useState<SalaryComponent[]>([]);
  const [structures, setStructures] = useState<SalaryStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [isSeeding, setIsSeeding] = useState(false);

  // Modals state
  const [isCompModalOpen, setIsCompModalOpen] = useState(false);
  const [isStructModalOpen, setIsStructModalOpen] = useState(false);
  const [isEditStructModalOpen, setIsEditStructModalOpen] = useState(false);
  const [editingStruct, setEditingStruct] = useState<SalaryStructure | null>(null);
  const [isEditCompModalOpen, setIsEditCompModalOpen] = useState(false);
  const [editingComp, setEditingComp] = useState<SalaryComponent | null>(null);

  // Structure Line Assignment state
  const [isAssignLineModalOpen, setIsAssignLineModalOpen] = useState(false);
  const [assignTargetStruct, setAssignTargetStruct] = useState<SalaryStructure | null>(null);
  const [selectedCompId, setSelectedCompId] = useState<string>("");
  const [assignCalcType, setAssignCalcType] = useState<CalculationType>("fixed");
  const [assignValue, setAssignValue] = useState<number>(0);
  const [isSubmittingAssign, setIsSubmittingAssign] = useState(false);

  // Delete Confirmation state
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Notification state
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Create Forms
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

  // Edit Forms
  const editStructForm = useForm<StructureFormData>({
    resolver: zodResolver(structureFormSchema),
    defaultValues: {
      code: "",
      name: "",
      name_bn: "",
      description: "",
      is_active: true,
    },
  });

  const editCompForm = useForm<ComponentFormData>({
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

  // Open Edit Structure
  const handleOpenEditStruct = (struct: SalaryStructure) => {
    setEditingStruct(struct);
    editStructForm.reset({
      code: struct.code,
      name: struct.name,
      name_bn: struct.name_bn || "",
      description: struct.description || "",
      is_active: struct.is_active,
    });
    setIsEditStructModalOpen(true);
  };

  // Edit Structure Submit
  const handleEditStructSubmit = async (data: StructureFormData) => {
    if (!editingStruct) return;
    try {
      await payrollApi.updateStructure(editingStruct.id, data);
      setIsEditStructModalOpen(false);
      setEditingStruct(null);
      setNotification({ type: "success", message: t("payroll.structUpdated", "Salary structure updated successfully.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.structUpdateFailed", "Failed to update salary structure.") });
    }
  };

  // Open Edit Component
  const handleOpenEditComp = (comp: SalaryComponent) => {
    setEditingComp(comp);
    editCompForm.reset({
      code: comp.code,
      name_en: comp.name_en,
      name_bn: comp.name_bn || "",
      component_type: comp.component_type,
      calculation_type: comp.calculation_type,
      default_value: Number(comp.default_value) || 0,
      is_taxable: comp.is_taxable,
      is_active: comp.is_active,
      display_order: comp.display_order ?? 10,
    });
    setIsEditCompModalOpen(true);
  };

  // Edit Component Submit
  const handleEditCompSubmit = async (data: ComponentFormData) => {
    if (!editingComp) return;
    try {
      await payrollApi.updateComponent(editingComp.id, {
        ...data,
        default_value: data.default_value.toString(),
      });
      setIsEditCompModalOpen(false);
      setEditingComp(null);
      setNotification({ type: "success", message: t("payroll.compUpdated", "Salary component updated successfully.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.compUpdateFailed", "Failed to update salary component.") });
    }
  };

  // Open Assign Component Line Modal
  const handleOpenAssignLine = (struct: SalaryStructure) => {
    setAssignTargetStruct(struct);
    // Find unassigned components first
    const assignedCompIds = new Set((struct.lines || []).map((l) => l.component));
    const available = components.filter((c) => !assignedCompIds.has(c.id));
    const initialComp = available.length > 0 ? available[0] : components[0];

    if (initialComp) {
      setSelectedCompId(initialComp.id);
      setAssignCalcType(initialComp.calculation_type);
      setAssignValue(Number(initialComp.default_value) || 0);
    } else {
      setSelectedCompId("");
      setAssignCalcType("fixed");
      setAssignValue(0);
    }
    setIsAssignLineModalOpen(true);
  };

  // Select Component in Assign Modal
  const handleSelectCompForAssign = (compId: string) => {
    setSelectedCompId(compId);
    const comp = components.find((c) => c.id === compId);
    if (comp) {
      setAssignCalcType(comp.calculation_type);
      setAssignValue(Number(comp.default_value) || 0);
    }
  };

  // Assign Component Line Submit
  const handleAssignLineSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignTargetStruct || !selectedCompId) return;

    setIsSubmittingAssign(true);
    try {
      await payrollApi.addStructureLine({
        structure: assignTargetStruct.id,
        component: selectedCompId,
        calculation_type: assignCalcType,
        value: assignValue.toString(),
      });
      setIsAssignLineModalOpen(false);
      setNotification({ type: "success", message: t("payroll.lineAssigned", "Component assigned to salary structure.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.lineAssignFailed", "Failed to assign component to structure.") });
    } finally {
      setIsSubmittingAssign(false);
    }
  };

  // Confirm Delete Action
  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      if (deleteTarget.type === "structure") {
        await payrollApi.deleteStructure(deleteTarget.id);
        setNotification({ type: "success", message: t("payroll.structDeleted", "Salary structure deleted successfully.") });
      } else if (deleteTarget.type === "component") {
        await payrollApi.deleteComponent(deleteTarget.id);
        setNotification({ type: "success", message: t("payroll.compDeleted", "Salary component deleted successfully.") });
      } else if (deleteTarget.type === "line") {
        await payrollApi.deleteStructureLine(deleteTarget.id);
        setNotification({ type: "success", message: t("payroll.lineDeleted", "Component removed from salary structure.") });
      }
      setDeleteTarget(null);
      void fetchData();
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.deleteFailed", "Failed to delete item. It may be in use by other records."),
      });
    } finally {
      setIsDeleting(false);
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
                  <div className="flex items-start justify-between gap-2">
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
                    <div className="flex items-center gap-1.5 shrink-0">
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
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenEditStruct(struct)}
                        className="h-7 w-7 p-0 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                        title={t("common.edit", "Edit Structure")}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setDeleteTarget({
                            type: "structure",
                            id: struct.id,
                            name: `${struct.name} (${struct.code})`,
                          })
                        }
                        className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                        title={t("common.delete", "Delete Structure")}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>

                  {struct.description && (
                    <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
                      {struct.description}
                    </p>
                  )}

                  {/* Components summary table */}
                  <div className="border rounded-lg overflow-hidden text-xs">
                    <div className="bg-slate-50 dark:bg-slate-800 px-3 py-1.5 font-semibold text-slate-600 dark:text-slate-300 flex justify-between items-center">
                      <span>{t("payroll.component", "Component")}</span>
                      <div className="flex items-center gap-2">
                        <span>{t("payroll.rule", "Calculation Rule")}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenAssignLine(struct)}
                          className="h-5 px-1.5 text-xs text-emerald-700 hover:text-emerald-800 hover:bg-emerald-100 dark:text-emerald-400 dark:hover:bg-emerald-950 font-semibold gap-1"
                          title={t("payroll.assignComponent", "Assign Component")}
                        >
                          <Plus className="h-3 w-3" />
                          {t("payroll.assign", "Assign")}
                        </Button>
                      </div>
                    </div>
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      {struct.lines && struct.lines.length > 0 ? (
                        struct.lines.map((line) => (
                          <div key={line.id} className="px-3 py-1.5 flex justify-between items-center group">
                            <span className="text-slate-700 dark:text-slate-300 font-medium">
                              {line.component_name_en}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-slate-600 dark:text-slate-400">
                                {line.calculation_type === "percentage_of_basic"
                                  ? `${line.value}% Basic`
                                  : line.calculation_type === "percentage_of_gross"
                                  ? `${line.value}% Gross`
                                  : `৳${line.value}`}
                              </span>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  setDeleteTarget({
                                    type: "line",
                                    id: line.id,
                                    name: `${line.component_name_en} from ${struct.name}`,
                                    structureId: struct.id,
                                  })
                                }
                                className="h-5 w-5 p-0 text-slate-300 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 opacity-70 group-hover:opacity-100 transition-opacity"
                                title={t("common.remove", "Remove component from structure")}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="px-3 py-3 text-slate-400 text-center flex flex-col items-center justify-center gap-1.5">
                          <span className="italic">{t("payroll.noComponentsAssigned", "No components assigned.")}</span>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenAssignLine(struct)}
                            className="h-7 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950 gap-1"
                          >
                            <Plus className="h-3 w-3" />
                            {t("payroll.assignComponent", "Assign Component")}
                          </Button>
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
                  <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500">
                      {t("common.loading", "Loading components...")}
                    </td>
                  </tr>
                ) : filteredComponents.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500">
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
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {c.is_system && (
                            <span
                              className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 mr-1"
                              title="Core system component (cannot be deleted)"
                            >
                              System
                            </span>
                          )}
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenEditComp(c)}
                            className="h-7 w-7 p-0 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                            title={t("common.edit", "Edit Component")}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setDeleteTarget({
                                type: "component",
                                id: c.id,
                                name: `${c.name_en} (${c.code})`,
                              })
                            }
                            disabled={c.is_system}
                            className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 disabled:opacity-30 disabled:pointer-events-none"
                            title={
                              c.is_system
                                ? t("payroll.systemCompNoDelete", "System components cannot be deleted")
                                : t("common.delete", "Delete Component")
                            }
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
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

      {/* Modal 3: Edit Structure */}
      <Dialog open={isEditStructModalOpen} onOpenChange={setIsEditStructModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.editStructureTitle", "Edit Salary Structure Template")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void editStructForm.handleSubmit(handleEditStructSubmit)(e);
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("common.code", "Code")}</FormLabel>
                <Input placeholder="e.g. SNR-TCHR" {...editStructForm.register("code")} />
                {editStructForm.formState.errors.code && (
                  <FormMessage>{editStructForm.formState.errors.code.message}</FormMessage>
                )}
              </FormField>
              <FormField>
                <FormLabel>{t("common.name", "Template Name")}</FormLabel>
                <Input placeholder="e.g. Senior Teacher Grade" {...editStructForm.register("name")} />
                {editStructForm.formState.errors.name && (
                  <FormMessage>{editStructForm.formState.errors.name.message}</FormMessage>
                )}
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.nameBn", "Name (Bangla)")}</FormLabel>
              <Input placeholder="e.g. জ্যেষ্ঠ শিক্ষক স্কেল" {...editStructForm.register("name_bn")} />
            </FormField>

            <FormField>
              <FormLabel>{t("common.description", "Description")}</FormLabel>
              <Input placeholder="Structure notes..." {...editStructForm.register("description")} />
            </FormField>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="struct_is_active"
                {...editStructForm.register("is_active")}
                className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
              />
              <label htmlFor="struct_is_active" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {t("payroll.isActiveStructure", "Structure template is active")}
              </label>
            </div>

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsEditStructModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("common.saveChanges", "Save Changes")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 4: Edit Component */}
      <Dialog open={isEditCompModalOpen} onOpenChange={setIsEditCompModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.editComponentTitle", "Edit Salary Component")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void editCompForm.handleSubmit(handleEditCompSubmit)(e);
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("common.code", "Code")}</FormLabel>
                <Input
                  placeholder="e.g. HRA, MED, PF"
                  disabled={editingComp?.is_system}
                  {...editCompForm.register("code")}
                />
                {editCompForm.formState.errors.code && (
                  <FormMessage>{editCompForm.formState.errors.code.message}</FormMessage>
                )}
              </FormField>
              <FormField>
                <FormLabel>{t("payroll.type", "Type")}</FormLabel>
                <select
                  disabled={editingComp?.is_system}
                  {...editCompForm.register("component_type")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 disabled:opacity-60"
                >
                  <option value="earning">{t("payroll.earning", "Earning")}</option>
                  <option value="deduction">{t("payroll.deduction", "Deduction")}</option>
                </select>
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.nameEn", "Name (English)")}</FormLabel>
              <Input placeholder="e.g. House Rent Allowance" {...editCompForm.register("name_en")} />
              {editCompForm.formState.errors.name_en && (
                <FormMessage>{editCompForm.formState.errors.name_en.message}</FormMessage>
              )}
            </FormField>

            <FormField>
              <FormLabel>{t("payroll.nameBn", "Name (Bangla)")}</FormLabel>
              <Input placeholder="e.g. বাড়ি ভাড়া ভাতা" {...editCompForm.register("name_bn")} />
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.calculationType", "Calculation Rule")}</FormLabel>
                <select
                  {...editCompForm.register("calculation_type")}
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
                  {...editCompForm.register("default_value", { valueAsNumber: true })}
                />
              </FormField>
            </div>

            <div className="flex items-center gap-6 pt-1">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="comp_is_taxable"
                  {...editCompForm.register("is_taxable")}
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                />
                <label htmlFor="comp_is_taxable" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {t("payroll.taxableIncome", "Taxable")}
                </label>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="comp_is_active"
                  {...editCompForm.register("is_active")}
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                />
                <label htmlFor="comp_is_active" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {t("common.active", "Active")}
                </label>
              </div>
            </div>

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsEditCompModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("common.saveChanges", "Save Changes")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 5: Assign Component to Structure */}
      <Dialog open={isAssignLineModalOpen} onOpenChange={setIsAssignLineModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.assignComponentTitle", "Assign Component to Structure")}
            </DialogTitle>
          </DialogHeader>
          {assignTargetStruct && (
            <form onSubmit={(e) => { void handleAssignLineSubmit(e); }} className="space-y-4">
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-900/40">
                <p className="text-xs text-emerald-800 dark:text-emerald-300 font-medium">
                  {t("payroll.targetStructure", "Target Structure")}:{" "}
                  <strong className="font-bold">{assignTargetStruct.name}</strong> ({assignTargetStruct.code})
                </p>
              </div>

              <FormField>
                <FormLabel>{t("payroll.selectComponent", "Select Component")}</FormLabel>
                <select
                  value={selectedCompId}
                  onChange={(e) => handleSelectCompForAssign(e.target.value)}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                  required
                >
                  <option value="" disabled>
                    -- {t("payroll.chooseComponent", "Choose a salary component")} --
                  </option>
                  {components.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.code} - {c.name_en} ({c.component_type === "earning" ? "Earning" : "Deduction"})
                    </option>
                  ))}
                </select>
              </FormField>

              <div className="grid grid-cols-2 gap-3">
                <FormField>
                  <FormLabel>{t("payroll.calculationRule", "Calculation Rule")}</FormLabel>
                  <select
                    value={assignCalcType}
                    onChange={(e) => setAssignCalcType(e.target.value as CalculationType)}
                    className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                  >
                    <option value="fixed">Fixed BDT Amount</option>
                    <option value="percentage_of_basic">% of Basic Salary</option>
                    <option value="percentage_of_gross">% of Gross Salary</option>
                  </select>
                </FormField>
                <FormField>
                  <FormLabel>{t("payroll.valueOrPercent", "Value / Rate")}</FormLabel>
                  <Input
                    type="number"
                    step="0.01"
                    value={assignValue}
                    onChange={(e) => setAssignValue(Number(e.target.value))}
                    required
                  />
                </FormField>
              </div>

              <DialogFooter className="pt-3">
                <Button type="button" variant="outline" onClick={() => setIsAssignLineModalOpen(false)}>
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmittingAssign || !selectedCompId}
                  className="bg-emerald-700 hover:bg-emerald-800 text-white"
                >
                  {isSubmittingAssign
                    ? t("common.saving", "Assigning...")
                    : t("payroll.assignComponent", "Assign Component")}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Modal 6: Delete Confirmation */}
      <Dialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2 text-rose-600">
              <AlertTriangle className="h-5 w-5" />
              {deleteTarget?.type === "structure"
                ? t("payroll.deleteStructureTitle", "Delete Salary Structure")
                : deleteTarget?.type === "component"
                ? t("payroll.deleteComponentTitle", "Delete Salary Component")
                : t("payroll.removeLineTitle", "Remove Component from Structure")}
            </DialogTitle>
          </DialogHeader>

          <div className="py-2 text-sm text-slate-600 dark:text-slate-300 space-y-2">
            <p>
              {deleteTarget?.type === "line"
                ? t(
                    "payroll.confirmRemoveLine",
                    "Are you sure you want to remove this component rule from the salary structure?"
                  )
                : t("payroll.confirmDeleteGeneric", "Are you sure you want to delete this record? This action cannot be undone.")}
            </p>
            {deleteTarget && (
              <div className="p-2.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-xs text-slate-800 dark:text-slate-200">
                {deleteTarget.name}
              </div>
            )}
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={isDeleting}
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              type="button"
              onClick={() => { void handleConfirmDelete(); }}
              disabled={isDeleting}
              className="bg-rose-600 hover:bg-rose-700 text-white"
            >
              {isDeleting
                ? t("common.deleting", "Deleting...")
                : deleteTarget?.type === "line"
                ? t("common.remove", "Remove")
                : t("common.delete", "Delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
