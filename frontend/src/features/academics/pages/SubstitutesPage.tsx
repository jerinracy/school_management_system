import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Plus,
  UserCheck,
  Trash2,
  Calendar,
  BookOpen,
  Clock,
  AlertCircle,
  Search,
  User,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";
import {
  academicApi,
  type Substitute,
  type ClassLevel,
  type Section,
  type RoutineSlot,
} from "@/features/academics/api/academicApi";
import { staffApi, type StaffListItem } from "@/features/staff/api/staffApi";

const WEEKDAYS = [
  { id: 0, label: "Saturday", bn: "শনিবার" },
  { id: 1, label: "Sunday", bn: "রবিবার" },
  { id: 2, label: "Monday", bn: "সোমবার" },
  { id: 3, label: "Tuesday", bn: "মঙ্গলবার" },
  { id: 4, label: "Wednesday", bn: "বুধবার" },
  { id: 5, label: "Thursday", bn: "বৃহস্পতিবার" },
  { id: 6, label: "Friday", bn: "শুক্রবার" },
];

function getNctbWeekday(dateStr: string): number {
  if (!dateStr) return 0;
  const [y, m, d] = dateStr.split("-").map(Number);
  if (!y || !m || !d) return 0;
  const dt = new Date(y, m - 1, d);
  return (dt.getDay() + 1) % 7;
}

export function SubstitutesPage() {
  const { t, i18n } = useTranslation();
  const [substitutes, setSubstitutes] = useState<Substitute[]>([]);
  const [openModal, setOpenModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);

  // Form State
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [reason, setReason] = useState("");
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [sections, setSections] = useState<Section[]>([]);
  const [selectedSection, setSelectedSection] = useState<string>("");
  const [routineSlots, setRoutineSlots] = useState<RoutineSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<string>("");
  const [teachers, setTeachers] = useState<StaffListItem[]>([]);
  const [selectedTeacher, setSelectedTeacher] = useState<string>("");

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [filterDate, setFilterDate] = useState("");

  const loadData = useCallback(async () => {
    try {
      const data = await academicApi.getSubstitutes();
      setSubstitutes(data);
    } catch {
      toast.error(t("academics.loadSubstitutesError", "Failed to load substitute assignments."));
    }
  }, [t]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Load base classes and teaching staff
  const loadBaseFormMetadata = useCallback(async () => {
    try {
      const [clsList, staffList] = await Promise.all([
        academicApi.getClasses(),
        staffApi.getStaffList({ staff_type: "teacher" }).catch(() => ({ results: [] as StaffListItem[] })),
      ]);
      setClasses(clsList);
      setTeachers(staffList.results || []);
      if (clsList.length > 0 && clsList[0]) {
        setSelectedClass((prev) => (prev ? prev : clsList[0]!.id));
      }
    } catch {
      // Handled silently
    }
  }, []);

  useEffect(() => {
    if (openModal) {
      void loadBaseFormMetadata();
    }
  }, [openModal, loadBaseFormMetadata]);

  // When selected class changes, load sections
  useEffect(() => {
    if (openModal && selectedClass) {
      void academicApi.getSections({ class_level: selectedClass }).then((secs) => {
        setSections(secs);
        if (secs.length > 0 && secs[0]) {
          setSelectedSection((prev) => (secs.some((s) => s.id === prev) ? prev : secs[0]!.id));
        } else {
          setSelectedSection("");
          setRoutineSlots([]);
          setSelectedSlot("");
        }
      });
    } else {
      setSections([]);
      setSelectedSection("");
    }
  }, [openModal, selectedClass]);

  // When selected section or date changes, load routine slots for that section and weekday
  useEffect(() => {
    if (openModal && selectedSection && date) {
      setIsLoadingSlots(true);
      const weekday = getNctbWeekday(date);
      void academicApi
        .getRoutine({ section: selectedSection, weekday })
        .then((slots) => {
          setRoutineSlots(slots);
          if (slots.length > 0 && slots[0]) {
            setSelectedSlot((prev) => (slots.some((s) => s.id === prev) ? prev : slots[0]!.id));
          } else {
            setSelectedSlot("");
          }
        })
        .finally(() => {
          setIsLoadingSlots(false);
        });
    } else {
      setRoutineSlots([]);
      setSelectedSlot("");
    }
  }, [openModal, selectedSection, date]);

  // Currently selected routine slot details
  const activeSlot = useMemo(() => {
    return routineSlots.find((s) => s.id === selectedSlot) || null;
  }, [routineSlots, selectedSlot]);

  const currentWeekdayObj = useMemo(() => {
    const wId = getNctbWeekday(date || "");
    return WEEKDAYS.find((w) => w.id === wId) || WEEKDAYS[0]!;
  }, [date]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSlot || !selectedTeacher || !date) {
      toast.error(t("common.required", "Please fill in all required fields."));
      return;
    }

    setIsSubmitting(true);
    try {
      await academicApi.createSubstitute({
        routine_slot: selectedSlot,
        slot_date: date,
        substitute_staff: selectedTeacher,
        teacher: selectedTeacher,
        reason: reason.trim() || undefined,
      });
      toast.success(t("academics.substituteCreated", "Substitute teacher assigned."));
      setOpenModal(false);
      setReason("");
      setSelectedSlot("");
      setSelectedTeacher("");
      void loadData();
    } catch {
      toast.error(t("academics.substituteCreateError", "Failed to assign substitute."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (
      !window.confirm(
        t(
          "academics.confirmDeleteSubstitute",
          "Are you sure you want to revoke this substitute cover allocation?",
        ),
      )
    ) {
      return;
    }
    try {
      await academicApi.deleteSubstitute(id);
      toast.success(t("academics.substituteDeleted", "Cover assignment removed successfully."));
      setSubstitutes((prev) => prev.filter((s) => s.id !== id));
    } catch {
      toast.error(t("academics.substituteDeleteError", "Failed to remove cover assignment."));
    }
  };

  // Filtered list
  const filteredSubstitutes = useMemo(() => {
    return substitutes.filter((sub) => {
      const matchesDate = !filterDate || sub.slot_date === filterDate;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        (sub.substitute_teacher_name && sub.substitute_teacher_name.toLowerCase().includes(q)) ||
        (sub.original_teacher_name && sub.original_teacher_name.toLowerCase().includes(q)) ||
        ((sub as unknown as { class_level_name?: string }).class_level_name &&
          (sub as unknown as { class_level_name?: string }).class_level_name!.toLowerCase().includes(q)) ||
        ((sub as unknown as { section_name?: string }).section_name &&
          (sub as unknown as { section_name?: string }).section_name!.toLowerCase().includes(q)) ||
        ((sub as unknown as { subject_name_en?: string }).subject_name_en &&
          (sub as unknown as { subject_name_en?: string }).subject_name_en!.toLowerCase().includes(q)) ||
        (sub.reason && sub.reason.toLowerCase().includes(q));

      return matchesDate && matchesSearch;
    });
  }, [substitutes, filterDate, searchQuery]);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.substitutesTitle", "Teacher Substitutions & Cover Allocations")}
        subtitle={t(
          "academics.substitutesSubtitle",
          "Assign substitute teachers to cover classes during faculty leave or absence.",
        )}
      />

      {/* Filter and Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-ink-muted" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("academics.searchSubstitutes", "Search by teacher, class, section...")}
              className="pl-8 h-8 text-xs"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-ink-muted" />
            <Input
              type="date"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
              className="h-8 text-xs w-36"
              title={t("academics.filterByDate", "Filter by date")}
            />
            {filterDate && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 text-xs"
                onClick={() => setFilterDate("")}
              >
                {t("common.clear", "Clear")}
              </Button>
            )}
          </div>
        </div>

        <Button
          size="sm"
          onClick={() => {
            setReason("");
            setOpenModal(true);
          }}
        >
          <Plus className="h-3.5 w-3.5 mr-1" />
          {t("academics.addSubstitute", "Assign Cover")}
        </Button>
      </div>

      {/* Allocations Table Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-primary" />
            {t("academics.substitutesList", "Active Cover Assignments")}
            <Badge variant="neutral" className="ml-2 font-mono text-[10px]">
              {filteredSubstitutes.length}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredSubstitutes.length === 0 ? (
            <div className="py-12 text-center text-xs text-ink-muted">
              <Calendar className="h-8 w-8 mx-auto text-ink-subtle mb-2 opacity-50" />
              <p>{t("academics.noSubstitutes", "No substitute teacher assignments recorded.")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border border-border text-xs">
                <thead>
                  <tr className="bg-canvas text-ink-muted">
                    <th className="border border-border p-2 text-left font-semibold w-28">
                      {t("academics.date", "Date")}
                    </th>
                    <th className="border border-border p-2 text-left font-semibold">
                      {t("academics.classSection", "Class & Section")}
                    </th>
                    <th className="border border-border p-2 text-left font-semibold">
                      {t("academics.period", "Period / Time")}
                    </th>
                    <th className="border border-border p-2 text-left font-semibold">
                      {t("academics.subject", "Subject")}
                    </th>
                    <th className="border border-border p-2 text-left font-semibold">
                      {t("academics.substituteTeacher", "Cover Teacher (Taking Class)")}
                    </th>
                    <th className="border border-border p-2 text-left font-semibold">
                      {t("academics.originalTeacher", "Original Teacher")}
                    </th>
                    <th className="border border-border p-2 text-left font-semibold">
                      {t("academics.reason", "Reason")}
                    </th>
                    <th className="border border-border p-2 text-center font-semibold w-16">
                      {t("common.actions", "Actions")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredSubstitutes.map((sub) => {
                    const extra = sub as unknown as {
                      class_level_name?: string;
                      section_name?: string;
                      subject_name_en?: string;
                      subject_name_bn?: string;
                      subject_code?: string;
                      period_name?: string;
                      period_start?: string;
                      period_end?: string;
                      room_name?: string;
                    };
                    return (
                      <tr key={sub.id} className="hover:bg-canvas/50 transition-colors">
                        <td className="border border-border p-2.5 font-medium whitespace-nowrap">
                          <p className="font-semibold text-ink">
                            {formatDate(sub.slot_date, i18n.language)}
                          </p>
                          <p className="text-[10px] text-ink-muted">
                            {WEEKDAYS[getNctbWeekday(sub.slot_date || "")]?.label}
                          </p>
                        </td>
                        <td className="border border-border p-2.5 whitespace-nowrap">
                          {extra.class_level_name ? (
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-ink">{extra.class_level_name}</span>
                              <Badge variant="neutral" className="text-[10px] px-1 py-0">
                                {extra.section_name}
                              </Badge>
                            </div>
                          ) : (
                            <span className="text-ink-subtle">—</span>
                          )}
                        </td>
                        <td className="border border-border p-2.5 whitespace-nowrap">
                          <div className="flex items-center gap-1 text-ink">
                            <Clock className="h-3 w-3 text-ink-muted shrink-0" />
                            <span className="font-medium">{extra.period_name || t("academics.period", "Period")}</span>
                          </div>
                          {extra.period_start && extra.period_end && (
                            <p className="text-[10px] text-ink-muted font-mono mt-0.5">
                              {extra.period_start} - {extra.period_end}
                            </p>
                          )}
                        </td>
                        <td className="border border-border p-2.5">
                          <div className="flex items-center gap-1.5">
                            <BookOpen className="h-3 w-3 text-ink-muted shrink-0" />
                            <span className="font-medium text-ink">
                              {extra.subject_name_en || extra.subject_name_bn || sub.routine_summary || "—"}
                            </span>
                            {extra.subject_code && (
                              <span className="text-[10px] font-mono text-ink-subtle">
                                ({extra.subject_code})
                              </span>
                            )}
                          </div>
                          {extra.room_name && (
                            <p className="text-[10px] text-ink-muted mt-0.5">
                              Room: {extra.room_name}
                            </p>
                          )}
                        </td>
                        <td className="border border-border p-2.5">
                          <div className="flex items-center gap-1.5">
                            <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 px-2 py-0.5 font-semibold text-xs border border-emerald-500/20">
                              <UserCheck className="h-3 w-3" />
                              {sub.substitute_teacher_name || t("academics.substituteTeacher", "Cover Teacher")}
                            </span>
                          </div>
                        </td>
                        <td className="border border-border p-2.5 text-ink-muted">
                          {sub.original_teacher_name ? (
                            <span className="text-ink font-medium">{sub.original_teacher_name}</span>
                          ) : (
                            <span className="text-amber-600 dark:text-amber-400 font-medium">
                              {t("academics.noTeacherAssigned", "Unassigned")}
                            </span>
                          )}
                        </td>
                        <td className="border border-border p-2.5">
                          <span className="text-ink-muted italic">
                            {sub.reason || t("common.none", "None")}
                          </span>
                        </td>
                        <td className="border border-border p-2.5 text-center">
                          <button
                            type="button"
                            title={t("common.delete", "Delete")}
                            onClick={() => void handleDelete(sub.id)}
                            className="text-danger hover:text-danger/80 p-1 rounded hover:bg-danger/10 transition-colors"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Assign Substitute Cover Dialog */}
      <Dialog open={openModal} onOpenChange={setOpenModal}>
        <DialogContent closeLabel={t("common.close", "Close")} className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("academics.newSubstituteTitle", "Assign Substitute Cover")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreate(e)} className="space-y-3.5 pt-2">
            {/* Date Picker */}
            <FormField>
              <FormLabel required>{t("academics.date", "Date")}</FormLabel>
              <div className="flex items-center gap-2">
                <Input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  required
                  className="flex-1"
                />
                <Badge variant="neutral" className="h-9 px-3 text-xs font-semibold shrink-0">
                  {currentWeekdayObj.label} ({currentWeekdayObj.bn})
                </Badge>
              </div>
            </FormField>

            {/* Class & Section Selection */}
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.classGrade", "Class Grade")}</FormLabel>
                <Select value={selectedClass} onValueChange={setSelectedClass}>
                  <SelectTrigger>
                    <SelectValue placeholder={t("academics.selectClass", "Select Class")} />
                  </SelectTrigger>
                  <SelectContent>
                    {classes.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel required>{t("academics.section", "Section")}</FormLabel>
                <Select
                  value={selectedSection}
                  onValueChange={setSelectedSection}
                  disabled={sections.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={
                        sections.length === 0
                          ? t("academics.noSections", "No Sections")
                          : t("academics.selectSection", "Select Section")
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {sections.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </div>

            {/* Scheduled Period Slot for this date */}
            <FormField>
              <FormLabel required>
                {t("academics.scheduledRoutinePeriod", "Period / Scheduled Class")}
              </FormLabel>
              <Select
                value={selectedSlot}
                onValueChange={setSelectedSlot}
                disabled={isLoadingSlots || routineSlots.length === 0}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      isLoadingSlots
                        ? t("common.loading", "Loading...")
                        : routineSlots.length === 0
                          ? t("academics.noSlotsForDate", "No routine periods on this day")
                          : t("academics.selectRoutineSlot", "Select period slot...")
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {routineSlots.map((slot) => (
                    <SelectItem key={slot.id} value={slot.id}>
                      {slot.period_name || "Period"} ({slot.period_start} - {slot.period_end}) •{" "}
                      {slot.subject_name_en || "Subject"} • [
                      {slot.teacher_name || t("academics.noTeacherAssigned", "Unassigned")}]
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {routineSlots.length === 0 && selectedSection && !isLoadingSlots && (
                <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                  {t(
                    "academics.noSlotsForDate",
                    "No routine periods scheduled for this section on this day.",
                  )}
                </p>
              )}
            </FormField>

            {/* Display Active Slot Summary if selected */}
            {activeSlot && (
              <div className="rounded-md border border-border bg-canvas/60 p-2.5 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink">
                    {activeSlot.subject_name_en || "Subject"} ({activeSlot.period_name})
                  </span>
                  {activeSlot.room_name && (
                    <span className="text-[10px] text-ink-muted font-mono">
                      Room: {activeSlot.room_name}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-ink-muted">
                  {t("academics.originalTeacher", "Original Teacher")}:{" "}
                  <span className="font-medium text-ink">
                    {activeSlot.teacher_name || t("academics.noTeacherAssigned", "Unassigned")}
                  </span>
                </p>
              </div>
            )}

            {/* Substitute Teacher (Who will take class) */}
            <FormField>
              <FormLabel required>
                {t("academics.substituteTeacher", "Substitute Teacher (Who will take class)")}
              </FormLabel>
              <Select value={selectedTeacher} onValueChange={setSelectedTeacher}>
                <SelectTrigger>
                  <SelectValue
                    placeholder={t("academics.selectTeacher", "Select teacher...")}
                  />
                </SelectTrigger>
                <SelectContent>
                  {teachers.map((teach) => {
                    const isOriginal =
                      activeSlot &&
                      ((activeSlot as unknown as { teacher_staff?: string }).teacher_staff ===
                        teach.id ||
                        activeSlot.teacher_name ===
                          (teach.full_name_en || teach.full_name_bn));
                    return (
                      <SelectItem
                        key={teach.id}
                        value={teach.id}
                        disabled={Boolean(isOriginal)}
                      >
                        <div className="flex items-center gap-1.5">
                          <User className="h-3 w-3 text-ink-muted shrink-0" />
                          <span>{teach.full_name_en || teach.full_name_bn}</span>
                          <span className="text-[10px] text-ink-muted font-mono">
                            ({teach.designation_title || teach.employee_id})
                            {isOriginal && " - Original Teacher"}
                          </span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </FormField>

            {/* Reason */}
            <FormField>
              <FormLabel required>{t("academics.reason", "Reason for Substitution")}</FormLabel>
              <Input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                placeholder="e.g. Medical Leave / Official Training / Emergency"
              />
            </FormField>

            <Button
              type="submit"
              className="w-full mt-2"
              disabled={isSubmitting || !selectedSlot || !selectedTeacher}
            >
              {isSubmitting
                ? t("common.saving", "Assigning...")
                : t("common.create", "Assign Cover")}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
