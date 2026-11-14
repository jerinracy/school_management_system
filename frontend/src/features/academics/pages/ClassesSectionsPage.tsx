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

export function ClassesSectionsPage() {
  const { t } = useTranslation();
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
      const cls = await academicApi.getClasses();
      setClasses(cls);
      if (cls.length > 0 && !selectedClass && cls[0]) {
        setSelectedClass(cls[0].id);
      }
    } catch {
      toast.error(t("academics.loadClassesError", "Failed to load classes."));
    }
  }, [t, selectedClass]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (selectedClass) {
      void academicApi.getSections(selectedClass).then(setSections);
    }
  }, [selectedClass]);

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await academicApi.createClass({
        name: className,
        code: classCode,
        numeric_order: classNumeric,
      });
      toast.success(t("academics.classCreated", "Class level created."));
      setOpenClassModal(false);
      setClassName("");
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
                    <p className="font-semibold text-sm text-ink">{sec.name}</p>
                    <p className="mt-1 text-[11px] text-ink-muted">
                      {t("academics.shift", "Shift")}: <span className="font-mono font-medium text-ink">{sec.shift_name || "—"}</span>
                    </p>
                    <p className="text-[11px] text-ink-muted">
                      {t("academics.capacity", "Capacity")}: <span className="font-mono font-medium text-ink">{sec.capacity || 50}</span>
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
