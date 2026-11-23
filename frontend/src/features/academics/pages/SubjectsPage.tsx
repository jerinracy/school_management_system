import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { BookOpen, Check, Layers, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { academicApi, type ClassLevel, type ClassSubject, type Subject } from "@/features/academics/api/academicApi";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";

export function SubjectsPage() {
  const { t } = useTranslation();
  const { selectedSession, selectedShift, selectedBranch } = useAcademicContextStore();
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [classSubjects, setClassSubjects] = useState<ClassSubject[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");

  // Modals
  const [openSubjectModal, setOpenSubjectModal] = useState(false);
  const [openEditSubjectModal, setOpenEditSubjectModal] = useState(false);
  const [openOfferingModal, setOpenOfferingModal] = useState(false);
  const [openEditOfferingModal, setOpenEditOfferingModal] = useState(false);

  // Edit / Delete states
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null);
  const [subjectToDelete, setSubjectToDelete] = useState<Subject | null>(null);

  const [editingOffering, setEditingOffering] = useState<ClassSubject | null>(null);
  const [offeringToDelete, setOfferingToDelete] = useState<ClassSubject | null>(null);

  // Form states - Create Subject
  const [sNameEn, setSNameEn] = useState("");
  const [sNameBn, setSNameBn] = useState("");
  const [sCode, setSCode] = useState("");
  const [sType, setSType] = useState("compulsory");

  // Form states - Edit Subject
  const [editSNameEn, setEditSNameEn] = useState("");
  const [editSNameBn, setEditSNameBn] = useState("");
  const [editSCode, setEditSCode] = useState("");
  const [editSType, setEditSType] = useState("compulsory");

  // Form states - Map Offering
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [totalMarks, setTotalMarks] = useState(100);
  const [passMarks, setPassMarks] = useState(33);

  // Form states - Edit Offering
  const [editTotalMarks, setEditTotalMarks] = useState(100);
  const [editPassMarks, setEditPassMarks] = useState(33);

  const loadData = useCallback(async () => {
    try {
      const [cls, subs] = await Promise.all([
        academicApi.getClasses({
          shift: selectedShift?.id,
          session: selectedSession?.id,
          branch: selectedBranch?.id,
        }),
        academicApi.getSubjects(),
      ]);
      setClasses(cls);
      setSubjects(subs);
      if (cls.length > 0 && !selectedClass && cls[0]) {
        setSelectedClass(cls[0].id);
      }
    } catch {
      toast.error(t("academics.loadSubjectsError", "Failed to load subjects."));
    }
  }, [t, selectedClass, selectedShift?.id, selectedSession?.id, selectedBranch?.id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (selectedClass) {
      void academicApi.getClassSubjects(selectedClass).then(setClassSubjects);
    }
  }, [selectedClass]);

  const handleCreateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const finalEn = sNameEn.trim() || sNameBn.trim();
      const finalBn = sNameBn.trim() || sNameEn.trim();
      await academicApi.createSubject({
        name_en: finalEn,
        name_bn: finalBn,
        name: finalEn,
        code: sCode.trim(),
        type: sType,
        subject_type: sType,
      });
      toast.success(t("academics.subjectCreated", "Subject added to catalog."));
      setOpenSubjectModal(false);
      setSNameEn("");
      setSNameBn("");
      setSCode("");
      setSType("compulsory");
      void loadData();
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.subjectCreateError", "Failed to add subject.");
      toast.error(msg);
    }
  };

  const handleOpenEditSubject = (sub: Subject) => {
    setEditingSubject(sub);
    setEditSNameEn(sub.name_en || "");
    setEditSNameBn(sub.name_bn || "");
    setEditSCode(sub.code || "");
    setEditSType(sub.type || "compulsory");
    setOpenEditSubjectModal(true);
  };

  const handleUpdateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSubject) return;
    try {
      await academicApi.updateSubject(editingSubject.id, {
        name_en: editSNameEn.trim(),
        name_bn: editSNameBn.trim(),
        code: editSCode.trim(),
        type: editSType,
        subject_type: editSType,
      });
      toast.success(t("academics.subjectUpdated", "Subject catalog updated."));
      setOpenEditSubjectModal(false);
      setEditingSubject(null);
      void loadData();
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.subjectUpdateError", "Failed to update subject.");
      toast.error(msg);
    }
  };

  const handleDeleteSubject = async () => {
    if (!subjectToDelete) return;
    try {
      await academicApi.deleteSubject(subjectToDelete.id);
      toast.success(t("academics.subjectDeleted", "Subject removed from catalog (soft deleted)."));
      setSubjects((prev) => prev.filter((s) => s.id !== subjectToDelete.id));
      void loadData();
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.subjectDeleteError", "Failed to delete subject.");
      toast.error(msg);
    } finally {
      setSubjectToDelete(null);
    }
  };

  const handleCreateOffering = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await academicApi.createClassSubject({
        class_level: selectedClass,
        subject: selectedSubjectId,
        session: selectedSession?.id,
        total_marks: totalMarks,
        full_marks: totalMarks,
        pass_marks: passMarks,
        pass_rule: { pass_marks: passMarks },
      });
      toast.success(t("academics.offeringCreated", "Subject mapped to class grade."));
      setOpenOfferingModal(false);
      void academicApi.getClassSubjects(selectedClass).then(setClassSubjects);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.offeringCreateError", "Failed to map subject.");
      toast.error(msg);
    }
  };

  const handleOpenEditOffering = (cs: ClassSubject) => {
    setEditingOffering(cs);
    setEditTotalMarks(Number(cs.full_marks || 100));
    const passRule = cs.pass_rule as Record<string, unknown> | null | undefined;
    setEditPassMarks(Number(passRule?.pass_marks || 33));
    setOpenEditOfferingModal(true);
  };

  const handleUpdateOffering = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingOffering) return;
    try {
      await academicApi.updateClassSubject(editingOffering.id, {
        total_marks: editTotalMarks,
        full_marks: editTotalMarks,
        pass_rule: { pass_marks: editPassMarks },
      });
      toast.success(t("academics.offeringUpdated", "Subject offering updated."));
      setOpenEditOfferingModal(false);
      setEditingOffering(null);
      void academicApi.getClassSubjects(selectedClass).then(setClassSubjects);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.offeringUpdateError", "Failed to update offering.");
      toast.error(msg);
    }
  };

  const handleDeleteOffering = async () => {
    if (!offeringToDelete) return;
    try {
      await academicApi.deleteClassSubject(offeringToDelete.id);
      toast.success(t("academics.offeringDeleted", "Subject mapping removed."));
      setClassSubjects((prev) => prev.filter((cs) => cs.id !== offeringToDelete.id));
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("academics.offeringDeleteError", "Failed to remove offering.");
      toast.error(msg);
    } finally {
      setOfferingToDelete(null);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.subjectsTitle", "Curriculum Subjects & Evaluation Components")}
        subtitle={t("academics.subjectsSubtitle", "Catalog theory, practical, and optional subjects and map them to grades with pass mark rules.")}
      />

      <Tabs defaultValue="mapped" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="mapped" className="flex items-center gap-1.5">
            <BookOpen className="h-3.5 w-3.5" />
            {t("academics.mappedSubjectsTab", "Class Mapped Subjects")}
          </TabsTrigger>
          <TabsTrigger value="catalog" className="flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5" />
            {t("academics.masterCatalogTab", "Master Subject Catalog")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="mapped" className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <label className="text-xs font-semibold text-ink">{t("academics.selectClass", "Select Class Grade:")}</label>
              <Select value={selectedClass} onValueChange={setSelectedClass}>
                <SelectTrigger className="w-48 h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {classes.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button size="sm" onClick={() => setOpenOfferingModal(true)} disabled={!selectedClass}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              {t("academics.mapToClass", "Map Subject to this Class")}
            </Button>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-primary" />
                {t("academics.mappedSubjectsList", "Subjects Taught in")} {classes.find((c) => c.id === selectedClass)?.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {classSubjects.length === 0 ? (
                <p className="text-xs text-ink-muted">{t("academics.noMappedSubjects", "No subjects assigned to this class yet.")}</p>
              ) : (
                <div className="divide-y divide-border">
                  {classSubjects.map((cs) => (
                    <div key={cs.id} className="flex items-center justify-between py-2.5 text-xs">
                      <div>
                        <p className="font-semibold text-ink">
                          {cs.subject_name_en || "Subject"}
                          <span className="ml-2 font-mono text-[10px] text-ink-muted">({cs.subject_code || "CODE"})</span>
                        </p>
                        <p className="text-[11px] text-ink-muted">
                          Total Marks: <span className="font-medium text-ink">{cs.full_marks || "100"}</span> | Pass:{" "}
                          <span className="font-medium text-ink">
                            {String((cs.pass_rule as Record<string, unknown> | null | undefined)?.pass_marks ?? "33")}
                          </span>
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
                          <Check className="h-3.5 w-3.5" />
                          Mapped
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-ink-muted hover:text-primary"
                          title={t("common.edit", "Edit Offering")}
                          onClick={() => handleOpenEditOffering(cs)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-danger hover:text-danger"
                          title={t("common.delete", "Remove Mapping")}
                          onClick={() => setOfferingToDelete(cs)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="catalog" className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-xs text-ink-muted">
              {t("academics.catalogSubtitle", "Standard curriculum subject catalog for the institution.")}
            </p>
            <Button size="sm" onClick={() => setOpenSubjectModal(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              {t("academics.addCatalogSubject", "New Catalog Subject")}
            </Button>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">{t("academics.catalogList", "Institution Subject Catalog")}</CardTitle>
            </CardHeader>
            <CardContent>
              {subjects.length === 0 ? (
                <p className="text-xs text-ink-muted">{t("academics.noCatalogSubjects", "No subjects in catalog.")}</p>
              ) : (
                <div className="divide-y divide-border">
                  {subjects.map((sub) => (
                    <div key={sub.id} className="flex items-center justify-between py-2.5 text-xs">
                      <div>
                        <p className="font-semibold text-ink">
                          {sub.name_en} {sub.name_bn ? `(${sub.name_bn})` : ""}
                          <span className="ml-2 font-mono text-[10px] text-ink-muted">Code: {sub.code}</span>
                        </p>
                        <p className="text-[11px] text-ink-muted capitalize">
                          Type: {sub.type_display || sub.type || "Compulsory"}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-ink-muted hover:text-primary"
                          title={t("common.edit", "Edit Subject")}
                          onClick={() => handleOpenEditSubject(sub)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-danger hover:text-danger"
                          title={t("common.delete", "Delete Subject")}
                          onClick={() => setSubjectToDelete(sub)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Catalog Subject Modal */}
      <Dialog open={openSubjectModal} onOpenChange={setOpenSubjectModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.newSubjectCatalog", "New Catalog Subject")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateSubject(e)} className="space-y-3 pt-2">
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.subjectNameEn", "Name (English)")}</FormLabel>
                <Input
                  value={sNameEn}
                  onChange={(e) => setSNameEn(e.target.value)}
                  required
                  placeholder="e.g. Mathematics"
                />
              </FormField>
              <FormField>
                <FormLabel>{t("academics.subjectNameBn", "Name (Bangla)")}</FormLabel>
                <Input
                  value={sNameBn}
                  onChange={(e) => setSNameBn(e.target.value)}
                  placeholder="e.g. গণিত"
                />
              </FormField>
            </div>
            <FormField>
              <FormLabel required>{t("academics.subjectCode", "Subject Code")}</FormLabel>
              <Input
                value={sCode}
                onChange={(e) => setSCode(e.target.value)}
                required
                placeholder="e.g. MATH-101"
              />
            </FormField>
            <FormField>
              <FormLabel required>{t("academics.subjectType", "Type")}</FormLabel>
              <Select value={sType} onValueChange={setSType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="compulsory">{t("academics.typeCompulsory", "Compulsory")}</SelectItem>
                  <SelectItem value="optional">{t("academics.typeOptional", "Optional / Elective")}</SelectItem>
                  <SelectItem value="fourth_subject">{t("academics.typeFourthSubject", "4th Subject")}</SelectItem>
                  <SelectItem value="co_curricular">{t("academics.typeCoCurricular", "Co-Curricular / Activity")}</SelectItem>
                </SelectContent>
              </Select>
            </FormField>
            <Button type="submit" className="w-full">{t("common.create", "Add to Catalog")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Catalog Subject Modal */}
      <Dialog open={openEditSubjectModal} onOpenChange={setOpenEditSubjectModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.editSubjectCatalog", "Edit Catalog Subject")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdateSubject(e)} className="space-y-3 pt-2">
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.subjectNameEn", "Name (English)")}</FormLabel>
                <Input
                  value={editSNameEn}
                  onChange={(e) => setEditSNameEn(e.target.value)}
                  required
                />
              </FormField>
              <FormField>
                <FormLabel>{t("academics.subjectNameBn", "Name (Bangla)")}</FormLabel>
                <Input
                  value={editSNameBn}
                  onChange={(e) => setEditSNameBn(e.target.value)}
                />
              </FormField>
            </div>
            <FormField>
              <FormLabel required>{t("academics.subjectCode", "Subject Code")}</FormLabel>
              <Input
                value={editSCode}
                onChange={(e) => setEditSCode(e.target.value)}
                required
              />
            </FormField>
            <FormField>
              <FormLabel required>{t("academics.subjectType", "Type")}</FormLabel>
              <Select value={editSType} onValueChange={setEditSType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="compulsory">{t("academics.typeCompulsory", "Compulsory")}</SelectItem>
                  <SelectItem value="optional">{t("academics.typeOptional", "Optional / Elective")}</SelectItem>
                  <SelectItem value="fourth_subject">{t("academics.typeFourthSubject", "4th Subject")}</SelectItem>
                  <SelectItem value="co_curricular">{t("academics.typeCoCurricular", "Co-Curricular / Activity")}</SelectItem>
                </SelectContent>
              </Select>
            </FormField>
            <Button type="submit" className="w-full">{t("common.saveChanges", "Save Changes")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Map Subject Offering Modal */}
      <Dialog open={openOfferingModal} onOpenChange={setOpenOfferingModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.mapSubjectTitle", "Map Subject to Grade")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateOffering(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.chooseSubject", "Subject")}</FormLabel>
              <Select value={selectedSubjectId} onValueChange={setSelectedSubjectId}>
                <SelectTrigger>
                  <SelectValue placeholder={t("academics.chooseSubjectPlaceholder", "Choose a subject...")} />
                </SelectTrigger>
                <SelectContent>
                  {subjects.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name_en || s.name_bn} ({s.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.totalMarks", "Total Full Marks")}</FormLabel>
                <Input type="number" value={totalMarks} onChange={(e) => setTotalMarks(Number(e.target.value))} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.passMarks", "Passing Marks")}</FormLabel>
                <Input type="number" value={passMarks} onChange={(e) => setPassMarks(Number(e.target.value))} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full" disabled={!selectedSubjectId}>
              {t("common.create", "Map Subject")}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Subject Offering Modal */}
      <Dialog open={openEditOfferingModal} onOpenChange={setOpenEditOfferingModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.editOfferingTitle", "Edit Subject Offering")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdateOffering(e)} className="space-y-3 pt-2">
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.totalMarks", "Total Full Marks")}</FormLabel>
                <Input type="number" value={editTotalMarks} onChange={(e) => setEditTotalMarks(Number(e.target.value))} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.passMarks", "Passing Marks")}</FormLabel>
                <Input type="number" value={editPassMarks} onChange={(e) => setEditPassMarks(Number(e.target.value))} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.saveChanges", "Save Changes")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Subject Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(subjectToDelete)}
        onOpenChange={(open) => { if (!open) setSubjectToDelete(null); }}
        title={t("academics.deleteSubjectTitle", "Delete Catalog Subject?")}
        description={t("academics.deleteSubjectDesc", `Are you sure you want to remove "${subjectToDelete?.name_en || ""}" from the master catalog? It will be soft-deleted.`)}
        confirmLabel={t("common.delete", "Delete Subject")}
        destructive
        onConfirm={() => void handleDeleteSubject()}
      />

      {/* Delete Offering Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(offeringToDelete)}
        onOpenChange={(open) => { if (!open) setOfferingToDelete(null); }}
        title={t("academics.deleteOfferingTitle", "Remove Subject from Class Grade?")}
        description={t("academics.deleteOfferingDesc", `Are you sure you want to unmap "${offeringToDelete?.subject_name_en}" from this class?`)}
        confirmLabel={t("common.delete", "Remove Mapping")}
        destructive
        onConfirm={() => void handleDeleteOffering()}
      />
    </div>
  );
}
