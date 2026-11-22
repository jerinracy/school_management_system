import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Layers, Plus, Users } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { academicApi, type ClassLevel, type Section } from "@/features/academics/api/academicApi";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";

export function ClassesSectionsPage() {
  const { t } = useTranslation();
  const { selectedShift, selectedSession, selectedBranch } = useAcademicContextStore();
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");

  const [openClassModal, setOpenClassModal] = useState(false);
  const [openBulkSectionModal, setOpenBulkSectionModal] = useState(false);

  const [className, setClassName] = useState("");
  const [classCode, setClassCode] = useState("");
  const [classNumeric, setClassNumeric] = useState(1);

  const [bulkNames, setBulkNames] = useState("A, B, C");

  const loadData = useCallback(async () => {
    try {
      const cls = await academicApi.getClasses({
        shift: selectedShift?.id,
        session: selectedSession?.id,
        branch: selectedBranch?.id,
      });
      setClasses(cls);
      if (cls.length > 0) {
        if (!selectedClass || !cls.some((c) => c.id === selectedClass)) {
          setSelectedClass(cls[0]?.id || "");
        }
      } else {
        setSelectedClass("");
        setSections([]);
      }
    } catch {
      toast.error(t("academics.loadClassesError", "Failed to load classes."));
    }
  }, [t, selectedClass, selectedShift?.id, selectedSession?.id, selectedBranch?.id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (selectedClass) {
      void academicApi
        .getSections({
          class_level: selectedClass,
          shift: selectedShift?.id,
          session: selectedSession?.id,
          branch: selectedBranch?.id,
        })
        .then(setSections);
    } else {
      setSections([]);
    }
  }, [selectedClass, selectedShift?.id, selectedSession?.id, selectedBranch?.id]);

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await academicApi.createClass({
        name: className,
        code: classCode,
        order: Number(classNumeric),
        numeric_order: Number(classNumeric),
        shift: selectedShift?.id,
        session: selectedSession?.id,
        branch: selectedBranch?.id,
      });
      toast.success(t("academics.classCreated", "Class level created."));
      setOpenClassModal(false);
      setClassName("");
      setClassCode("");
      void loadData();
    } catch {
      toast.error(t("academics.classCreateError", "Failed to create class."));
    }
  };

  const handleBulkCreateSections = async (e: React.FormEvent) => {
    e.preventDefault();
    const names = bulkNames
      .split(",")
      .map((n) => n.trim())
      .filter(Boolean);

    if (names.length === 0) return;

    try {
      await academicApi.bulkCreateSections({
        class_id: selectedClass,
        names,
        shift_id: selectedShift?.id,
        session_id: selectedSession?.id,
      });
      toast.success(t("academics.sectionsCreated", "Sections created in batch."));
      setOpenBulkSectionModal(false);
      void academicApi.getSections(selectedClass).then(setSections);
    } catch {
      toast.error(t("academics.sectionsCreateError", "Failed to create sections."));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.classesSectionsTitle", "Classes & Section Management")}
        subtitle={t("academics.classesSectionsSubtitle", "Manage standard national curriculum class grades (1-12) and batch-generate sections.")}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Classes Column */}
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              {t("academics.classList", "Class Levels")}
            </CardTitle>
            <Button size="sm" onClick={() => setOpenClassModal(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              {t("academics.addClass", "New")}
            </Button>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {classes.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedClass(c.id)}
                className={`w-full text-left rounded-md border p-2.5 transition-colors text-xs flex items-center justify-between ${
                  selectedClass === c.id ? "border-primary bg-primary/5 font-semibold text-primary" : "border-border hover:bg-canvas text-ink"
                }`}
              >
                <span>{c.name}</span>
                <span className="font-mono text-[10px] text-ink-muted">Order: {c.order}</span>
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Sections Column */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Users className="h-4 w-4 text-primary" />
                {t("academics.sectionsTitle", "Class Sections & Capacity")}
              </CardTitle>
              <p className="text-xs text-ink-muted">
                {classes.find((c) => c.id === selectedClass)?.name || "Select a class"}
              </p>
            </div>
            <Button size="sm" onClick={() => setOpenBulkSectionModal(true)} disabled={!selectedClass}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              {t("academics.bulkCreateSectionsBtn", "Batch Create Sections")}
            </Button>
          </CardHeader>
          <CardContent>
            {sections.length === 0 ? (
              <p className="text-xs text-ink-muted">{t("academics.noSections", "No sections configured for this class.")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                {sections.map((sec) => (
                  <div key={sec.id} className="rounded-md border border-border bg-canvas p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-sm text-ink">{sec.name}</p>
                      {sec.teacher_staff_name || sec.teacher_name ? (
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                          {sec.teacher_staff_name || sec.teacher_name}
                        </span>
                      ) : (
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400">
                          {t("academics.noTeacher", "No Teacher")}
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 text-[11px] text-ink-muted">
                      {t("academics.shift", "Shift")}: <span className="font-mono font-medium text-ink">{sec.shift_name || "—"}</span>
                    </p>
                    <p className="text-[11px] text-ink-muted">
                      {t("academics.capacity", "Capacity")}: <span className="font-mono font-medium text-ink">{sec.capacity || 50}</span>
                    </p>
                    <p className="text-[11px] text-ink-muted mt-0.5">
                      {t("academics.classTeacher", "Class Teacher")}:{" "}
                      <span className="font-medium text-ink">
                        {sec.teacher_staff_name || sec.teacher_name || t("academics.unassigned", "Unassigned")}
                      </span>
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* New Class Modal */}
      <Dialog open={openClassModal} onOpenChange={setOpenClassModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.newClassTitle", "Create Class Grade")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateClass(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.className", "Class Name")}</FormLabel>
              <Input value={className} onChange={(e) => setClassName(e.target.value)} required placeholder="e.g. Class 10 / Ten" />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.classCode", "Code")}</FormLabel>
                <Input value={classCode} onChange={(e) => setClassCode(e.target.value)} required placeholder="e.g. TEN" />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.numericOrder", "Numeric Order")}</FormLabel>
                <Input type="number" value={classNumeric} onChange={(e) => setClassNumeric(Number(e.target.value))} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.create", "Create Class")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Bulk Create Sections Modal */}
      <Dialog open={openBulkSectionModal} onOpenChange={setOpenBulkSectionModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.bulkSectionsTitle", "Batch Create Sections")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleBulkCreateSections(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.sectionNamesList", "Section Names (Comma Separated)")}</FormLabel>
              <Input value={bulkNames} onChange={(e) => setBulkNames(e.target.value)} required placeholder="e.g. Padma, Meghna, Jamuna or A, B, C" />
              <p className="mt-1 text-[11px] text-ink-muted">Each comma-separated name will instantiate an active section.</p>
            </FormField>
            <Button type="submit" className="w-full">{t("common.create", "Generate Sections")}</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
