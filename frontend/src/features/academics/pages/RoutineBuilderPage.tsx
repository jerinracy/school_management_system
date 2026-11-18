import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, CalendarCheck, CheckCircle2, Pencil, Plus, Trash2, UserX } from "lucide-react";
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
import { staffApi, type StaffListItem } from "@/features/staff/api/staffApi";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";

const WEEKDAYS = [
  { id: 0, key: "saturday", label: "Saturday" },
  { id: 1, key: "sunday", label: "Sunday" },
  { id: 2, key: "monday", label: "Monday" },
  { id: 3, key: "tuesday", label: "Tuesday" },
  { id: 4, key: "wednesday", label: "Wednesday" },
  { id: 5, key: "thursday", label: "Thursday" },
];

export function RoutineBuilderPage() {
  const { t } = useTranslation();
  const { selectedShift, selectedSession, selectedBranch } = useAcademicContextStore();
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [teachers, setTeachers] = useState<StaffListItem[]>([]);
  const [routine, setRoutine] = useState<RoutineSlot[]>([]);

  const [selectedClass, setSelectedClass] = useState<string>("");
  const [selectedSection, setSelectedSection] = useState<string>("");

  // Create slot modal state
  const [openSlotModal, setOpenSlotModal] = useState(false);
  const [slotDay, setSlotDay] = useState(0);
  const [slotPeriod, setSlotPeriod] = useState("");
  const [slotSubject, setSlotSubject] = useState("");
  const [slotRoom, setSlotRoom] = useState("");
  const [slotTeacher, setSlotTeacher] = useState("none");
  const [validationResult, setValidationResult] = useState<RoutineValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  // Edit slot / assign teacher modal state
  const [editingSlot, setEditingSlot] = useState<RoutineSlot | null>(null);
  const [openEditModal, setOpenEditModal] = useState(false);
  const [editTeacher, setEditTeacher] = useState("none");
  const [editRoom, setEditRoom] = useState("none");
  const [editSubject, setEditSubject] = useState("");
  const [editValidationResult, setEditValidationResult] = useState<RoutineValidationResult | null>(null);
  const [isEditValidating, setIsEditValidating] = useState(false);

  const loadBase = useCallback(async () => {
    try {
      const [cls, rawPers, subs, rms, stf] = await Promise.all([
        academicApi.getClasses({
          shift: selectedShift?.id,
          session: selectedSession?.id,
          branch: selectedBranch?.id,
        }),
        academicApi.getPeriods({ shift: selectedShift?.id }),
        academicApi.getSubjects(),
        academicApi.getRooms({ branch: selectedBranch?.id }),
        staffApi.getStaffList({ staff_type: "teacher" }).catch(() => ({ results: [] as StaffListItem[] })),
      ]);
      const pers = rawPers.length > 0 ? rawPers : await academicApi.getPeriods();
      setClasses(cls);
      setPeriods(pers);
      setSubjects(subs);
      setRooms(rms);
      setTeachers(stf.results || []);
      const assignable = pers.filter((p) => !p.is_break);
      if (cls.length > 0 && cls[0]) setSelectedClass((prev) => (prev ? prev : cls[0]!.id));
      if (assignable.length > 0 && assignable[0]) {
        setSlotPeriod((prev) => (prev && assignable.some((p) => p.id === prev) ? prev : assignable[0]!.id));
      }
      if (subs.length > 0 && subs[0]) setSlotSubject((prev) => (prev ? prev : subs[0]!.id));
      if (rms.length > 0 && rms[0]) setSlotRoom((prev) => (prev ? prev : rms[0]!.id));
    } catch {
      toast.error(t("academics.loadRoutineBaseError", "Failed to load timetable base data."));
    }
  }, [t, selectedShift?.id, selectedSession?.id, selectedBranch?.id]);

  useEffect(() => {
    void loadBase();
  }, [loadBase]);

  useEffect(() => {
    if (selectedSection && sections.length > 0) {
      const currentSec = sections.find((s) => s.id === selectedSection);
      const secShiftId = currentSec?.shift || selectedShift?.id;
      if (secShiftId) {
        void academicApi.getPeriods({ shift: secShiftId }).then((pList) => {
          if (pList.length > 0) {
            setPeriods(pList);
            const assignable = pList.filter((p) => !p.is_break);
            if (assignable.length > 0 && assignable[0]) {
              setSlotPeriod((prev) => (prev && assignable.some((p) => p.id === prev) ? prev : assignable[0]!.id));
            }
          }
        });
      }
    }
  }, [selectedSection, sections, selectedShift?.id]);

  useEffect(() => {
    if (selectedClass) {
      void academicApi
        .getSections({
          class_level: selectedClass,
          shift: selectedShift?.id,
          session: selectedSession?.id,
          branch: selectedBranch?.id,
        })
        .then((secs) => {
          setSections(secs);
          if (secs.length > 0) {
            setSelectedSection((prev) => (secs.some((s) => s.id === prev) ? prev : secs[0]!.id));
          } else {
            setSelectedSection("");
          }
        });
    } else {
      setSections([]);
      setSelectedSection("");
    }
  }, [selectedClass, selectedShift?.id, selectedSession?.id, selectedBranch?.id]);

  const loadRoutine = useCallback(async () => {
    if (!selectedSection) {
      setRoutine([]);
      return;
    }
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
    const finalRoom = slotRoom && slotRoom !== "none" ? slotRoom : null;
    const finalTeacher = slotTeacher && slotTeacher !== "none" ? slotTeacher : null;
    try {
      const res = await academicApi.validateRoutineSlot({
        section_id: selectedSection,
        section: selectedSection,
        period_id: slotPeriod,
        period: slotPeriod,
        weekday: slotDay,
        room_id: finalRoom,
        room: finalRoom,
        teacher_staff_id: finalTeacher,
        teacher: finalTeacher,
        subject: slotSubject,
      });
      setValidationResult(res);
    } catch {
      // Handled by validation display
    } finally {
      setIsValidating(false);
    }
  };

  const handleCreateSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSection || !slotPeriod || !slotSubject) return;

    const finalRoom = slotRoom && slotRoom !== "none" ? slotRoom : null;
    const finalTeacher = slotTeacher && slotTeacher !== "none" ? slotTeacher : null;

    try {
      await academicApi.createRoutineSlot({
        section: selectedSection,
        weekday: slotDay,
        period: slotPeriod,
        subject: slotSubject,
        room: finalRoom,
        teacher_staff: finalTeacher,
        teacher: finalTeacher,
      });
      toast.success(t("academics.slotAssigned", "Timetable slot assigned."));
      setOpenSlotModal(false);
      setValidationResult(null);
      void loadRoutine();
    } catch {
      toast.error(t("academics.slotAssignError", "Failed to assign slot. Check for double booking conflicts."));
    }
  };

  const handleOpenEditSlot = (slot: RoutineSlot) => {
    setEditingSlot(slot);
    setEditSubject(slot.subject);
    setEditTeacher(slot.teacher_staff || slot.teacher_user || "none");
    setEditRoom(slot.room || "none");
    setEditValidationResult(null);
    setOpenEditModal(true);
  };

  const handleValidateEditSlot = async () => {
    if (!editingSlot) return;
    setIsEditValidating(true);
    setEditValidationResult(null);
    const finalRoom = editRoom && editRoom !== "none" ? editRoom : null;
    const finalTeacher = editTeacher && editTeacher !== "none" ? editTeacher : null;
    try {
      const res = await academicApi.validateRoutineSlot({
        section_id: editingSlot.section,
        section: editingSlot.section,
        period_id: editingSlot.period,
        period: editingSlot.period,
        weekday: editingSlot.weekday,
        room_id: finalRoom,
        room: finalRoom,
        teacher_staff_id: finalTeacher,
        teacher: finalTeacher,
        subject: editSubject,
        exclude_slot_id: editingSlot.id,
      });
      setEditValidationResult(res);
    } catch {
      // Handled by validation result display
    } finally {
      setIsEditValidating(false);
    }
  };

  const handleUpdateSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSlot) return;
    const finalRoom = editRoom && editRoom !== "none" ? editRoom : null;
    const finalTeacher = editTeacher && editTeacher !== "none" ? editTeacher : null;

    try {
      await academicApi.updateRoutineSlot(editingSlot.id, {
        subject: editSubject,
        room: finalRoom,
        teacher_staff: finalTeacher,
        teacher: finalTeacher,
      });
      toast.success(t("academics.slotUpdated", "Timetable slot updated successfully."));
      setOpenEditModal(false);
      setEditingSlot(null);
      void loadRoutine();
    } catch {
      toast.error(t("academics.slotUpdateError", "Failed to update slot. Check for double booking conflicts."));
    }
  };

  const handleDeleteSlot = async (id: string) => {
    try {
      await academicApi.deleteRoutineSlot(id);
      toast.success(t("academics.slotDeleted", "Slot removed."));
      setRoutine((prev) => prev.filter((s) => s.id !== id));
      if (editingSlot?.id === id) {
        setOpenEditModal(false);
        setEditingSlot(null);
      }
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
              <SelectTrigger className="w-40 h-8 text-xs">
                <SelectValue placeholder={t("academics.selectClass", "Select Class")} />
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
            <Select value={selectedSection} onValueChange={setSelectedSection} disabled={sections.length === 0}>
              <SelectTrigger className="w-40 h-8 text-xs">
                <SelectValue placeholder={sections.length === 0 ? t("academics.noSections", "No Sections") : t("academics.selectSection", "Select Section")} />
              </SelectTrigger>
              <SelectContent>
                {sections.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button
          size="sm"
          onClick={() => {
            setSlotTeacher("none");
            setValidationResult(null);
            setOpenSlotModal(true);
          }}
          disabled={!selectedSection}
        >
          <Plus className="h-3.5 w-3.5 mr-1" />
          {t("academics.assignSlot", "Assign Period Slot")}
        </Button>
      </div>

      {/* Timetable Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center justify-between">
            <span className="flex items-center gap-2">
              <CalendarCheck className="h-4 w-4 text-primary" />
              {t("academics.weeklyGrid", "Weekly Schedule Grid")}
            </span>
            <span className="text-xs font-normal text-ink-muted">
              {t("academics.clickCellToAssignOrEdit", "Click empty cells to assign • Click slots to edit or assign teacher")}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full border-collapse border border-border text-xs">
            <thead>
              <tr className="bg-canvas">
                <th className="border border-border p-2 text-left font-semibold w-24">
                  {t("academics.day", "Day")}
                </th>
                {periods.map((p) => (
                  <th
                    key={p.id}
                    className={`border border-border p-2 text-center font-semibold ${
                      p.is_break ? "bg-canvas/80 text-ink-muted" : ""
                    }`}
                  >
                    <p>{p.name} {p.is_break && `(${t("academics.break", "Break")})`}</p>
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
                    if (period.is_break) {
                      return (
                        <td
                          key={period.id}
                          className="border border-border p-1.5 text-center align-middle bg-canvas/60 text-ink-muted select-none min-w-24"
                        >
                          <span className="text-[10px] font-semibold tracking-wider uppercase opacity-70">
                            {period.name}
                          </span>
                        </td>
                      );
                    }
                    const match = routine.find(
                      (r) => Number(r.weekday) === day.id && r.period === period.id,
                    );
                    return (
                      <td key={period.id} className="border border-border p-1.5 text-center align-top min-w-36">
                        {match ? (
                          <div
                            role="button"
                            tabIndex={0}
                            onClick={() => handleOpenEditSlot(match)}
                            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleOpenEditSlot(match); }}
                            className="group relative rounded border border-border bg-surface p-2 shadow-sm cursor-pointer hover:border-primary/50 hover:shadow transition-all text-left"
                          >
                            <p className="font-semibold text-ink leading-tight text-xs truncate">
                              {match.subject_name_en || "Subject"}
                            </p>
                            {match.teacher_name ? (
                              <p className="text-[11px] text-ink-muted leading-tight mt-1 truncate">
                                {match.teacher_name}
                              </p>
                            ) : (
                              <div className="mt-1">
                                <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 px-1.5 py-0.5 text-[9px] font-medium border border-amber-500/20">
                                  <UserX className="h-2.5 w-2.5" />
                                  {t("academics.noTeacherAssigned", "No Teacher")}
                                </span>
                              </div>
                            )}
                            {match.room_name && (
                              <p className="text-[10px] text-ink-subtle font-mono mt-0.5">{match.room_name}</p>
                            )}
                            <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 flex items-center gap-1 bg-surface/90 rounded p-0.5 transition-opacity">
                              <button
                                type="button"
                                title={t("common.edit", "Edit")}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenEditSlot(match);
                                }}
                                className="text-primary hover:text-primary/80 p-0.5"
                              >
                                <Pencil className="h-3 w-3" />
                              </button>
                              <button
                                type="button"
                                title={t("common.delete", "Delete")}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  void handleDeleteSlot(match.id);
                                }}
                                className="text-danger hover:text-danger/80 p-0.5"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            type="button"
                            disabled={!selectedSection}
                            title={selectedSection ? t("academics.clickToAssign", "Click to assign period") : undefined}
                            onClick={() => {
                              if (!selectedSection) return;
                              setSlotDay(day.id);
                              setSlotPeriod(period.id);
                              setSlotTeacher("none");
                              setValidationResult(null);
                              setOpenSlotModal(true);
                            }}
                            className="w-full h-14 rounded border border-dashed border-transparent hover:border-primary/40 hover:bg-primary/5 flex items-center justify-center transition-all group/cell disabled:opacity-40 disabled:hover:bg-transparent"
                          >
                            <Plus className="h-3.5 w-3.5 text-primary opacity-0 group-hover/cell:opacity-100 transition-opacity" />
                            <span className="text-[11px] text-ink-subtle group-hover/cell:hidden">—</span>
                          </button>
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

      {/* Assign New Slot Dialog */}
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
                  <SelectTrigger><SelectValue placeholder={t("academics.selectPeriod", "Select Period")} /></SelectTrigger>
                  <SelectContent>
                    {periods.filter((p) => !p.is_break).map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name} ({p.start_time} - {p.end_time})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </div>

            <FormField>
              <FormLabel required>{t("academics.subject", "Subject")}</FormLabel>
              <Select value={slotSubject} onValueChange={setSlotSubject}>
                <SelectTrigger><SelectValue placeholder={t("academics.selectSubject", "Select Subject")} /></SelectTrigger>
                <SelectContent>
                  {subjects.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.name_en || s.name_bn} ({s.code})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("academics.teacherOptional", "Teacher (Optional - Assign Later)")}</FormLabel>
                <Select value={slotTeacher} onValueChange={setSlotTeacher}>
                  <SelectTrigger><SelectValue placeholder={t("academics.selectTeacher", "Select teacher...")} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">-- {t("academics.noneAssignLater", "None (Assign Later)")} --</SelectItem>
                    {teachers.map((teach) => (
                      <SelectItem key={teach.id} value={teach.id}>
                        {teach.full_name_en || teach.full_name_bn} ({teach.designation_title || teach.employee_id})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("academics.room", "Room (Optional)")}</FormLabel>
                <Select value={slotRoom} onValueChange={setSlotRoom}>
                  <SelectTrigger><SelectValue placeholder={t("academics.selectRoom", "Select classroom...")} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">-- {t("common.none", "None")} --</SelectItem>
                    {rooms.map((r) => (
                      <SelectItem key={r.id} value={r.id}>{r.name} (Cap: {r.capacity})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </div>

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

      {/* Edit Slot / Assign Teacher Dialog */}
      <Dialog open={openEditModal} onOpenChange={setOpenEditModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.editSlotTitle", "Edit Routine Slot / Assign Teacher")}</DialogTitle>
          </DialogHeader>
          {editingSlot && (
            <form onSubmit={(e) => void handleUpdateSlot(e)} className="space-y-3 pt-2">
              <div className="rounded-md bg-canvas p-2.5 text-xs border border-border space-y-1">
                <div className="flex justify-between">
                  <span className="text-ink-muted">{t("academics.day", "Day")}:</span>
                  <span className="font-medium text-ink">{WEEKDAYS.find((d) => d.id === editingSlot.weekday)?.label}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-muted">{t("academics.period", "Period")}:</span>
                  <span className="font-medium text-ink">{editingSlot.period_name} ({editingSlot.period_start} - {editingSlot.period_end})</span>
                </div>
              </div>

              <FormField>
                <FormLabel required>{t("academics.subject", "Subject")}</FormLabel>
                <Select value={editSubject} onValueChange={setEditSubject}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {subjects.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.name_en || s.name_bn} ({s.code})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <div className="grid grid-cols-2 gap-3">
                <FormField>
                  <FormLabel>{t("academics.teacherOptional", "Teacher (Optional - Assign Later)")}</FormLabel>
                  <Select value={editTeacher} onValueChange={setEditTeacher}>
                    <SelectTrigger><SelectValue placeholder={t("academics.selectTeacher", "Select teacher...")} /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">-- {t("academics.noneAssignLater", "None (Assign Later)")} --</SelectItem>
                      {teachers.map((teach) => (
                        <SelectItem key={teach.id} value={teach.id}>
                          {teach.full_name_en || teach.full_name_bn} ({teach.designation_title || teach.employee_id})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>

                <FormField>
                  <FormLabel>{t("academics.room", "Room (Optional)")}</FormLabel>
                  <Select value={editRoom} onValueChange={setEditRoom}>
                    <SelectTrigger><SelectValue placeholder={t("academics.selectRoom", "Select classroom...")} /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">-- {t("common.none", "None")} --</SelectItem>
                      {rooms.map((r) => (
                        <SelectItem key={r.id} value={r.id}>{r.name} (Cap: {r.capacity})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
              </div>

              <div className="pt-2">
                <Button type="button" variant="outline" size="sm" onClick={() => void handleValidateEditSlot()} disabled={isEditValidating} className="w-full mb-2">
                  {isEditValidating ? t("common.checking", "Checking Conflicts...") : t("academics.checkConflicts", "Validate Conflict Pre-Check")}
                </Button>

                {editValidationResult && (
                  <div
                    className={`rounded-md p-2.5 text-xs mb-3 flex items-start gap-2 ${
                      editValidationResult.is_valid ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
                    }`}
                  >
                    {editValidationResult.is_valid ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="font-semibold">
                        {editValidationResult.is_valid ? t("academics.slotAvailable", "Slot Available (No Clashes)") : t("academics.conflictDetected", "Scheduling Conflict Detected")}
                      </p>
                      {editValidationResult.errors?.map((err, i) => (
                        <p key={i} className="text-[11px] mt-0.5">{err}</p>
                      ))}
                      {editValidationResult.warnings?.map((warn, i) => (
                        <p key={`w-${i}`} className="text-[11px] mt-0.5 text-amber-600">{warn}</p>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    className="w-1/3"
                    onClick={() => void handleDeleteSlot(editingSlot.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5 mr-1" />
                    {t("common.delete", "Delete")}
                  </Button>
                  <Button type="submit" size="sm" className="w-2/3">
                    {t("common.saveChanges", "Save Changes")}
                  </Button>
                </div>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
