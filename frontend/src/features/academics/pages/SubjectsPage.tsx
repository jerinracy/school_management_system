import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { BookOpen, Check, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { academicApi, type ClassLevel, type ClassSubject, type Subject } from "@/features/academics/api/academicApi";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";

export function SubjectsPage() {
  const { t } = useTranslation();
  const { selectedSession, selectedShift, selectedBranch } = useAcademicContextStore();
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [classSubjects, setClassSubjects] = useState<ClassSubject[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");

  const [openSubjectModal, setOpenSubjectModal] = useState(false);
  const [openOfferingModal, setOpenOfferingModal] = useState(false);

  const [sNameEn, setSNameEn] = useState("");
  const [sNameBn, setSNameBn] = useState("");
  const [sCode, setSCode] = useState("");
  const [sType, setSType] = useState("compulsory");

  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [totalMarks, setTotalMarks] = useState(100);
  const [passMarks, setPassMarks] = useState(33);

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
    } catch {
      toast.error(t("academics.subjectCreateError", "Failed to add subject."));
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
    } catch {
      toast.error(t("academics.offeringCreateError", "Failed to map subject."));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.subjectsTitle", "Curriculum Subjects & Evaluation Components")}
        subtitle={t("academics.subjectsSubtitle", "Catalog theory, practical, and optional subjects and map them to grades with pass mark rules.")}
      />

      <div className="flex items-center justify-between">
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

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setOpenSubjectModal(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            {t("academics.addCatalogSubject", "Master Catalog Subject")}
          </Button>
          <Button size="sm" onClick={() => setOpenOfferingModal(true)} disabled={!selectedClass}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            {t("academics.mapToClass", "Map to this Class")}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
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
                      Total Marks: <span className="font-medium text-ink">{cs.full_marks || "100"}</span>
                    </p>
                  </div>
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
                    <Check className="h-3.5 w-3.5" />
                    Mapped
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

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
                  <SelectValue placeholder="Choose a subject..." />
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
                <FormLabel required>{t("academics.totalMarks", "Total Marks")}</FormLabel>
                <Input type="number" value={totalMarks} onChange={(e) => setTotalMarks(Number(e.target.value))} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.passMarks", "Pass Marks")}</FormLabel>
                <Input type="number" value={passMarks} onChange={(e) => setPassMarks(Number(e.target.value))} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.create", "Confirm Mapping")}</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
