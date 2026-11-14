import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, CalendarCheck, CheckCircle2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  academicApi,
  type ClassLevel,
  type Period,
  type Room,
  type RoutineSlot,
  type RoutineValidationResult,
  type Section,
  type Subject,
} from "@/features/academics/api/academicApi";

const WEEKDAYS = [
  { id: 0, key: "sunday", label: "Sunday" },
  { id: 1, key: "monday", label: "Monday" },
  { id: 2, key: "tuesday", label: "Tuesday" },
  { id: 3, key: "wednesday", label: "Wednesday" },
  { id: 4, key: "thursday", label: "Thursday" },
];

export function RoutineBuilderPage() {
  const { t } = useTranslation();
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [routine, setRoutine] = useState<RoutineSlot[]>([]);

  const [selectedClass, setSelectedClass] = useState<string>("");
  const [selectedSection, setSelectedSection] = useState<string>("");

  const [openSlotModal, setOpenSlotModal] = useState(false);
  const [slotDay, setSlotDay] = useState(0);
  const [slotPeriod, setSlotPeriod] = useState("");
  const [slotSubject, setSlotSubject] = useState("");
  const [slotRoom, setSlotRoom] = useState("");

  const [validationResult, setValidationResult] = useState<RoutineValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const loadBase = useCallback(async () => {
    try {
      const [cls, pers, subs, rms] = await Promise.all([
        academicApi.getClasses(),
        academicApi.getPeriods(),
        academicApi.getSubjects(),
        academicApi.getRooms(),
      ]);
      setClasses(cls);
      setPeriods(pers);
      setSubjects(subs);
      setRooms(rms);
      if (cls.length > 0 && cls[0]) setSelectedClass(cls[0].id);
      if (pers.length > 0 && pers[0]) setSlotPeriod(pers[0].id);
      if (subs.length > 0 && subs[0]) setSlotSubject(subs[0].id);
      if (rms.length > 0 && rms[0]) setSlotRoom(rms[0].id);
    } catch {
      toast.error(t("academics.loadRoutineBaseError", "Failed to load timetable base data."));
    }
  }, [t]);

  useEffect(() => {
    void loadBase();
  }, [loadBase]);

  useEffect(() => {
    if (selectedClass) {
      void academicApi.getSections(selectedClass).then((secs) => {
        setSections(secs);
        if (secs.length > 0 && secs[0]) setSelectedSection(secs[0].id);
      });
    }
  }, [selectedClass]);

  const loadRoutine = useCallback(async () => {
    if (!selectedSection) return;
    try {
      const slots = await academicApi.getRoutine(selectedSection);
      setRoutine(slots);
    } catch {
      toast.error(t("academics.loadRoutineError", "Failed to load routine slots."));
    }
  }, [t, selectedSection]);

  useEffect(() => {
    void loadRoutine();
  }, [loadRoutine]);

  const handleValidateSlot = async () => {
    if (!selectedSection || !slotPeriod || !slotSubject) return;
    setIsValidating(true);
    setValidationResult(null);
    try {
      const res = await academicApi.validateRoutineSlot({
        section: selectedSection,
        period: slotPeriod,
        weekday: slotDay,
        room: slotRoom || undefined,
        subject: slotSubject,
      });
      setValidationResult(res);
    } catch {
      // Endpoint threw error or conflict
    } finally {
      setIsValidating(false);
    }
  };

  const handleCreateSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSection || !slotPeriod || !slotSubject) return;

    try {
      await academicApi.createRoutineSlot({
        section: selectedSection,
        weekday: slotDay,
        period: slotPeriod,
        subject: slotSubject,
        room: slotRoom || undefined,
      });
      toast.success(t("academics.slotAssigned", "Timetable slot assigned."));
      setOpenSlotModal(false);
      setValidationResult(null);
      void loadRoutine();
    } catch {
      toast.error(t("academics.slotAssignError", "Failed to assign slot. Check for double booking conflicts."));
    }
  };

  const handleDeleteSlot = async (id: string) => {
    try {
      await academicApi.deleteRoutineSlot(id);
      toast.success(t("academics.slotDeleted", "Slot removed."));
      setRoutine((prev) => prev.filter((s) => s.id !== id));
    } catch {
      toast.error(t("academics.slotDeleteError", "Failed to remove slot."));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.routineBuilderTitle", "Weekly Routine & Timetable Builder")}
        subtitle={t("academics.routineBuilderSubtitle", "Interactive schedule designer with automated teacher double-booking & room conflict verification.")}
      />

      {/* Selectors */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div>
            <label className="text-[11px] font-semibold text-ink-muted block">{t("academics.classGrade", "Class Grade")}</label>
            <Select value={selectedClass} onValueChange={setSelectedClass}>
              <SelectTrigger className="w-36 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {classes.map((c) => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-ink-muted block">{t("academics.section", "Section")}</label>
            <Select value={selectedSection} onValueChange={setSelectedSection}>
              <SelectTrigger className="w-36 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {sections.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button size="sm" onClick={() => { setOpenSlotModal(true); setValidationResult(null); }} disabled={!selectedSection}>
          <Plus className="h-3.5 w-3.5 mr-1" />
          {t("academics.assignSlot", "Assign Period Slot")}
        </Button>
      </div>

      {/* Timetable Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <CalendarCheck className="h-4 w-4 text-primary" />
            {t("academics.weeklyGrid", "Weekly Schedule Grid")}
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full border-collapse border border-border text-xs">
            <thead>
              <tr className="bg-canvas">
                <th className="border border-border p-2 text-left font-semibold w-24">Day</th>
                {periods.map((p) => (
                  <th key={p.id} className="border border-border p-2 text-center font-semibold">
                    <p>{p.name}</p>
                    <p className="text-[10px] text-ink-muted font-normal">{p.start_time} - {p.end_time}</p>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {WEEKDAYS.map((day) => (
                <tr key={day.id} className="hover:bg-canvas/50">
                  <td className="border border-border p-2.5 font-medium bg-canvas/30">{day.label}</td>
                  {periods.map((period) => {
                    const match = routine.find(
                      (r) => Number(r.weekday) === day.id && r.period === period.id,
                    );
                    return (
                      <td key={period.id} className="border border-border p-2 text-center align-top min-w-32">
                        {match ? (
                          <div className="group relative rounded border border-border bg-surface p-1.5 shadow-sm">
                            <p className="font-semibold text-ink leading-tight">{match.subject_name_en || "Subject"}</p>
                            <p className="text-[10px] text-ink-muted leading-tight">{match.teacher_name || "Teacher"}</p>
                            {match.room_name && (
                              <p className="text-[10px] text-ink-subtle font-mono">{match.room_name}</p>
                            )}
                            <button
                              type="button"
                              onClick={() => void handleDeleteSlot(match.id)}
                              className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 text-danger hover:text-danger p-0.5 transition-opacity"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        ) : (
                          <span className="text-[10px] text-ink-subtle">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Assign Slot Dialog */}
      <Dialog open={openSlotModal} onOpenChange={setOpenSlotModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.assignRoutineSlot", "Assign Routine Slot")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateSlot(e)} className="space-y-3 pt-2">
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.dayOfWeek", "Weekday")}</FormLabel>
                <Select value={String(slotDay)} onValueChange={(val) => setSlotDay(Number(val))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {WEEKDAYS.map((d) => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel required>{t("academics.period", "Period")}</FormLabel>
                <Select value={slotPeriod} onValueChange={setSlotPeriod}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {periods.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name} ({p.start_time})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </div>

            <FormField>
              <FormLabel required>{t("academics.subject", "Subject")}</FormLabel>
              <Select value={slotSubject} onValueChange={setSlotSubject}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {subjects.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.name_en || s.name_bn} ({s.code})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField>
              <FormLabel>{t("academics.room", "Room (Optional)")}</FormLabel>
              <Select value={slotRoom} onValueChange={setSlotRoom}>
                <SelectTrigger><SelectValue placeholder="Select classroom..." /></SelectTrigger>
                <SelectContent>
                  {rooms.map((r) => (
                    <SelectItem key={r.id} value={r.id}>{r.name} (Cap: {r.capacity})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <div className="pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => void handleValidateSlot()} disabled={isValidating} className="w-full mb-2">
                {isValidating ? t("common.checking", "Checking Conflicts...") : t("academics.checkConflicts", "Validate Conflict Pre-Check")}
              </Button>

              {validationResult && (
                <div
                  className={`rounded-md p-2.5 text-xs mb-3 flex items-start gap-2 ${
                    validationResult.is_valid ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
                  }`}
                >
                  {validationResult.is_valid ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="font-semibold">
                      {validationResult.is_valid ? t("academics.slotAvailable", "Slot Available (No Clashes)") : t("academics.conflictDetected", "Scheduling Conflict Detected")}
                    </p>
                    {validationResult.errors?.map((err, i) => (
                      <p key={i} className="text-[11px] mt-0.5">{err}</p>
                    ))}
                    {validationResult.warnings?.map((warn, i) => (
                      <p key={`w-${i}`} className="text-[11px] mt-0.5 text-amber-600">{warn}</p>
                    ))}
                  </div>
                </div>
              )}

              <Button type="submit" className="w-full">{t("common.save", "Save Routine Slot")}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
