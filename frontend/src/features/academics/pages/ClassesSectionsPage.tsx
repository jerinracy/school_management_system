import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Layers, Pencil, Plus, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
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

  // Create Modals
  const [openClassModal, setOpenClassModal] = useState(false);
  const [openBulkSectionModal, setOpenBulkSectionModal] = useState(false);

  // Edit Modals
  const [openEditClassModal, setOpenEditClassModal] = useState(false);
  const [editingClass, setEditingClass] = useState<ClassLevel | null>(null);
  const [editClassName, setEditClassName] = useState("");
  const [editClassCode, setEditClassCode] = useState("");
  const [editClassNumeric, setEditClassNumeric] = useState(1);

  const [openEditSectionModal, setOpenEditSectionModal] = useState(false);
  const [editingSection, setEditingSection] = useState<Section | null>(null);
  const [editSectionName, setEditSectionName] = useState("");
  const [editSectionCapacity, setEditSectionCapacity] = useState(50);

  // Delete states
  const [classToDelete, setClassToDelete] = useState<ClassLevel | null>(null);
  const [sectionToDelete, setSectionToDelete] = useState<Section | null>(null);

  // Create form states
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
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.classCreateError", "Failed to create class.");
      toast.error(msg);
    }
  };

  const handleOpenEditClass = (cls: ClassLevel) => {
    setEditingClass(cls);
    setEditClassName(cls.name);
    setEditClassCode(cls.code);
    setEditClassNumeric(cls.order);
    setOpenEditClassModal(true);
  };

  const handleUpdateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingClass) return;
    try {
      await academicApi.updateClass(editingClass.id, {
        name: editClassName,
        code: editClassCode,
        order: Number(editClassNumeric),
        numeric_order: Number(editClassNumeric),
      });
      toast.success(t("academics.classUpdated", "Class level updated."));
      setOpenEditClassModal(false);
      setEditingClass(null);
      void loadData();
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.classUpdateError", "Failed to update class.");
      toast.error(msg);
    }
  };

  const handleDeleteClass = async () => {
    if (!classToDelete) return;
    try {
      await academicApi.deleteClass(classToDelete.id);
      toast.success(t("academics.classDeleted", "Class level soft deleted."));
      setClasses((prev) => prev.filter((c) => c.id !== classToDelete.id));
      if (selectedClass === classToDelete.id) {
        setSelectedClass("");
      }
      void loadData();
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.classDeleteError", "Failed to delete class.");
      toast.error(msg);
    } finally {
      setClassToDelete(null);
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
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.sectionsCreateError", "Failed to create sections.");
      toast.error(msg);
    }
  };

  const handleOpenEditSection = (sec: Section) => {
    setEditingSection(sec);
    setEditSectionName(sec.name);
    setEditSectionCapacity(sec.capacity || 50);
    setOpenEditSectionModal(true);
  };

  const handleUpdateSection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSection) return;
    try {
      await academicApi.updateSection(editingSection.id, {
        name: editSectionName,
        capacity: Number(editSectionCapacity),
      });
      toast.success(t("academics.sectionUpdated", "Section updated."));
      setOpenEditSectionModal(false);
      setEditingSection(null);
      void academicApi.getSections(selectedClass).then(setSections);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.sectionUpdateError", "Failed to update section.");
      toast.error(msg);
    }
  };

  const handleDeleteSection = async () => {
    if (!sectionToDelete) return;
    try {
      await academicApi.deleteSection(sectionToDelete.id);
      toast.success(t("academics.sectionDeleted", "Section soft deleted."));
      setSections((prev) => prev.filter((s) => s.id !== sectionToDelete.id));
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.sectionDeleteError", "Failed to delete section.");
      toast.error(msg);
    } finally {
      setSectionToDelete(null);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.classesSectionsTitle", "Classes & Section Management")}
        subtitle={t("academics.classesSectionsSubtitle", "Manage standard national curriculum class grades (1-12) and sections.")}
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
              {t("academics.addClass", "New Class")}
            </Button>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {classes.map((c) => (
              <div
                key={c.id}
                role="button"
                tabIndex={0}
                onClick={() => setSelectedClass(c.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    setSelectedClass(c.id);
                  }
                }}
                className={`w-full text-left rounded-md border p-2.5 transition-colors text-xs flex items-center justify-between cursor-pointer ${
                  selectedClass === c.id ? "border-primary bg-primary/5 font-semibold text-primary" : "border-border hover:bg-canvas text-ink"
                }`}
              >
                <div>
                  <span className="font-medium">{c.name}</span>
                  <span className="ml-2 font-mono text-[10px] text-ink-muted">Order: {c.order}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 text-ink-muted hover:text-primary"
                    title={t("common.edit", "Edit Class")}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleOpenEditClass(c);
                    }}
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 text-ink-muted hover:text-danger"
                    title={t("common.delete", "Delete Class")}
                    onClick={(e) => {
                      e.stopPropagation();
                      setClassToDelete(c);
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
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
                {classes.find((c) => c.id === selectedClass)?.name || t("academics.selectClassPlaceholder", "Select a class")}
              </p>
            </div>
            <Button size="sm" onClick={() => setOpenBulkSectionModal(true)} disabled={!selectedClass}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              {t("academics.bulkCreateSectionsBtn", "Batch Create Sections")}
            </Button>
          </CardHeader>
          <CardContent>
            {sections.length === 0 ? (
              <p className="text-xs text-ink-muted">{t("academics.noSections", "No sections configured for this class in current session.")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                {sections.map((sec) => (
                  <div key={sec.id} className="rounded-md border border-border bg-canvas p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-sm text-ink">{sec.name}</p>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-ink-muted hover:text-primary"
                          title={t("common.edit", "Edit Section")}
                          onClick={() => handleOpenEditSection(sec)}
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-ink-muted hover:text-danger"
                          title={t("common.delete", "Delete Section")}
                          onClick={() => setSectionToDelete(sec)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <div className="mt-1">
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

      {/* Edit Class Modal */}
      <Dialog open={openEditClassModal} onOpenChange={setOpenEditClassModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.editClassTitle", "Edit Class Grade")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdateClass(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.className", "Class Name")}</FormLabel>
              <Input value={editClassName} onChange={(e) => setEditClassName(e.target.value)} required />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.classCode", "Code")}</FormLabel>
                <Input value={editClassCode} onChange={(e) => setEditClassCode(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.numericOrder", "Numeric Order")}</FormLabel>
                <Input type="number" value={editClassNumeric} onChange={(e) => setEditClassNumeric(Number(e.target.value))} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.saveChanges", "Save Changes")}</Button>
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

      {/* Edit Section Modal */}
      <Dialog open={openEditSectionModal} onOpenChange={setOpenEditSectionModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.editSectionTitle", "Edit Class Section")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdateSection(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.sectionName", "Section Name")}</FormLabel>
              <Input value={editSectionName} onChange={(e) => setEditSectionName(e.target.value)} required />
            </FormField>
            <FormField>
              <FormLabel required>{t("academics.capacity", "Capacity")}</FormLabel>
              <Input type="number" value={editSectionCapacity} onChange={(e) => setEditSectionCapacity(Number(e.target.value))} required />
            </FormField>
            <Button type="submit" className="w-full">{t("common.saveChanges", "Save Changes")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Class Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(classToDelete)}
        onOpenChange={(open) => { if (!open) setClassToDelete(null); }}
        title={t("academics.deleteClassTitle", "Delete Class Grade?")}
        description={t("academics.deleteClassDesc", `Are you sure you want to remove "${classToDelete?.name}"? It will be soft-deleted and preserved in archive records.`)}
        confirmLabel={t("common.delete", "Delete Class")}
        destructive
        onConfirm={() => void handleDeleteClass()}
      />

      {/* Delete Section Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(sectionToDelete)}
        onOpenChange={(open) => { if (!open) setSectionToDelete(null); }}
        title={t("academics.deleteSectionTitle", "Delete Class Section?")}
        description={t("academics.deleteSectionDesc", `Are you sure you want to remove section "${sectionToDelete?.name}"? It will be soft-deleted.`)}
        confirmLabel={t("common.delete", "Delete Section")}
        destructive
        onConfirm={() => void handleDeleteSection()}
      />
    </div>
  );
}
