import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Clock, DoorOpen, Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { academicApi, type Period, type Room } from "@/features/academics/api/academicApi";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";

export function PeriodsRoomsPage() {
  const { t } = useTranslation();
  const { selectedShift, selectedBranch } = useAcademicContextStore();
  const [periods, setPeriods] = useState<Period[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);

  const [openPeriodModal, setOpenPeriodModal] = useState(false);
  const [openRoomModal, setOpenRoomModal] = useState(false);

  // Period Create form
  const [pName, setPName] = useState("");
  const [pStart, setPStart] = useState("08:00");
  const [pEnd, setPEnd] = useState("08:45");
  const [pOrder, setPOrder] = useState(1);

  // Room Create form
  const [rNumber, setRNumber] = useState("");
  const [rCapacity, setRCapacity] = useState(50);
  const [rType, setRType] = useState("classroom");

  // Edit / Delete states
  const [editingPeriod, setEditingPeriod] = useState<Period | null>(null);
  const [editPName, setEditPName] = useState("");
  const [editPStart, setEditPStart] = useState("");
  const [editPEnd, setEditPEnd] = useState("");
  const [editPOrder, setEditPOrder] = useState(1);
  const [deletePeriodTarget, setDeletePeriodTarget] = useState<Period | null>(null);

  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [editRNumber, setEditRNumber] = useState("");
  const [editRCapacity, setEditRCapacity] = useState(50);
  const [editRType, setEditRType] = useState("classroom");
  const [deleteRoomTarget, setDeleteRoomTarget] = useState<Room | null>(null);

  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [p, r] = await Promise.all([academicApi.getPeriods(), academicApi.getRooms()]);
      setPeriods(p);
      setRooms(r);
    } catch {
      toast.error(t("academics.loadPeriodsRoomsError", "Failed to load periods and rooms."));
    }
  }, [t]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCreatePeriod = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await academicApi.createPeriod({
        name: pName,
        start_time: pStart,
        end_time: pEnd,
        order: Number(pOrder),
        period_order: Number(pOrder),
        shift: selectedShift?.id,
      });
      toast.success(t("academics.periodCreated", "Period slot created."));
      setOpenPeriodModal(false);
      setPName("");
      void loadData();
    } catch {
      toast.error(t("academics.periodCreateError", "Failed to create period slot."));
    }
  };

  const handleOpenEditPeriod = (p: Period) => {
    setEditingPeriod(p);
    setEditPName(p.name);
    setEditPStart(p.start_time);
    setEditPEnd(p.end_time);
    setEditPOrder(p.order || 1);
  };

  const handleUpdatePeriod = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPeriod) return;
    setSubmitting(true);
    try {
      await academicApi.updatePeriod(editingPeriod.id, {
        name: editPName,
        start_time: editPStart,
        end_time: editPEnd,
        order: Number(editPOrder),
        period_order: Number(editPOrder),
      });
      toast.success(t("academics.periodUpdated", "Period slot updated."));
      setEditingPeriod(null);
      void loadData();
    } catch {
      toast.error(t("academics.periodUpdateError", "Failed to update period slot."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeletePeriod = async () => {
    if (!deletePeriodTarget) return;
    setSubmitting(true);
    try {
      await academicApi.deletePeriod(deletePeriodTarget.id);
      toast.success(t("academics.periodDeleted", "Period slot deleted."));
      setDeletePeriodTarget(null);
      void loadData();
    } catch {
      toast.error(t("academics.periodDeleteError", "Failed to delete period slot."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await academicApi.createRoom({
        name: rNumber,
        room_number: rNumber,
        capacity: Number(rCapacity),
        type: rType.toLowerCase(),
        room_type: rType.toLowerCase(),
        branch: selectedBranch?.id,
      });
      toast.success(t("academics.roomCreated", "Room registered."));
      setOpenRoomModal(false);
      setRNumber("");
      void loadData();
    } catch {
      toast.error(t("academics.roomCreateError", "Failed to register room."));
    }
  };

  const handleOpenEditRoom = (r: Room) => {
    setEditingRoom(r);
    setEditRNumber(r.name || "");
    setEditRCapacity(r.capacity || 50);
    setEditRType(r.type || "classroom");
  };

  const handleUpdateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRoom) return;
    setSubmitting(true);
    try {
      await academicApi.updateRoom(editingRoom.id, {
        name: editRNumber,
        room_number: editRNumber,
        capacity: Number(editRCapacity),
        type: editRType.toLowerCase(),
        room_type: editRType.toLowerCase(),
      });
      toast.success(t("academics.roomUpdated", "Room updated."));
      setEditingRoom(null);
      void loadData();
    } catch {
      toast.error(t("academics.roomUpdateError", "Failed to update room."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteRoom = async () => {
    if (!deleteRoomTarget) return;
    setSubmitting(true);
    try {
      await academicApi.deleteRoom(deleteRoomTarget.id);
      toast.success(t("academics.roomDeleted", "Room deleted."));
      setDeleteRoomTarget(null);
      void loadData();
    } catch {
      toast.error(t("academics.roomDeleteError", "Failed to delete room."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.periodsRoomsTitle", "Daily Period Slots & Facility Rooms")}
        subtitle={t("academics.periodsRoomsSubtitle", "Configure bell timings, duration order, and classroom room capacity allocations.")}
      />

      <Tabs defaultValue="periods" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="periods" className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            {t("academics.periodsTab", "Daily Periods")}
          </TabsTrigger>
          <TabsTrigger value="rooms" className="flex items-center gap-1.5">
            <DoorOpen className="h-3.5 w-3.5" />
            {t("academics.roomsTab", "Classrooms & Labs")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="periods">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-semibold">{t("academics.periodsList", "Timetable Periods")}</CardTitle>
              <Button size="sm" onClick={() => setOpenPeriodModal(true)}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                {t("academics.addPeriod", "Add Period")}
              </Button>
            </CardHeader>
            <CardContent>
              {periods.length === 0 ? (
                <p className="text-xs text-ink-muted">{t("academics.noPeriods", "No periods created.")}</p>
              ) : (
                <div className="divide-y divide-border">
                  {periods.map((p) => (
                    <div key={p.id} className="flex items-center justify-between py-2.5 text-xs">
                      <div>
                        <p className="font-semibold text-ink">
                          {p.name}
                          <span className="ml-2 font-mono text-[10px] text-ink-muted">Order: {p.order}</span>
                        </p>
                        <p className="text-[11px] text-ink-muted font-mono">{p.start_time} – {p.end_time}</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-ink-muted hover:text-ink"
                          onClick={() => handleOpenEditPeriod(p)}
                          title={t("common.edit", "Edit")}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-ink-muted hover:text-rose-600"
                          onClick={() => setDeletePeriodTarget(p)}
                          title={t("common.delete", "Delete")}
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

        <TabsContent value="rooms">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-semibold">{t("academics.roomsList", "Campus Rooms")}</CardTitle>
              <Button size="sm" onClick={() => setOpenRoomModal(true)}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                {t("academics.addRoom", "Add Room")}
              </Button>
            </CardHeader>
            <CardContent>
              {rooms.length === 0 ? (
                <p className="text-xs text-ink-muted">{t("academics.noRooms", "No rooms registered.")}</p>
              ) : (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                  {rooms.map((r) => (
                    <div key={r.id} className="rounded-md border border-border bg-canvas p-3 text-xs flex flex-col justify-between">
                      <div>
                        <div className="flex items-start justify-between">
                          <p className="font-semibold text-sm text-ink">{r.name}</p>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 text-ink-muted hover:text-ink"
                              onClick={() => handleOpenEditRoom(r)}
                              title={t("common.edit", "Edit")}
                            >
                              <Pencil className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 text-ink-muted hover:text-rose-600"
                              onClick={() => setDeleteRoomTarget(r)}
                              title={t("common.delete", "Delete")}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        <p className="text-[11px] text-ink-muted mt-1">Type: {r.type_display || r.type || "General"}</p>
                        <p className="text-[11px] text-ink-muted">Capacity: {r.capacity} seats</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* New Period Dialog */}
      <Dialog open={openPeriodModal} onOpenChange={setOpenPeriodModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.newPeriodTitle", "New Period Slot")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreatePeriod(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.periodName", "Period Label")}</FormLabel>
              <Input value={pName} onChange={(e) => setPName(e.target.value)} required placeholder="e.g. 1st Period" />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.startTime", "Start Time")}</FormLabel>
                <Input type="time" value={pStart} onChange={(e) => setPStart(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.endTime", "End Time")}</FormLabel>
                <Input type="time" value={pEnd} onChange={(e) => setPEnd(e.target.value)} required />
              </FormField>
            </div>
            <FormField>
              <FormLabel required>{t("academics.periodOrder", "Numeric Order")}</FormLabel>
              <Input type="number" value={pOrder} onChange={(e) => setPOrder(Number(e.target.value))} required />
            </FormField>
            <Button type="submit" className="w-full">{t("common.create", "Create Period")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Period Dialog */}
      <Dialog open={!!editingPeriod} onOpenChange={(open) => !open && setEditingPeriod(null)}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.editPeriodTitle", "Edit Period Slot")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdatePeriod(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.periodName", "Period Label")}</FormLabel>
              <Input value={editPName} onChange={(e) => setEditPName(e.target.value)} required />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.startTime", "Start Time")}</FormLabel>
                <Input type="time" value={editPStart} onChange={(e) => setEditPStart(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.endTime", "End Time")}</FormLabel>
                <Input type="time" value={editPEnd} onChange={(e) => setEditPEnd(e.target.value)} required />
              </FormField>
            </div>
            <FormField>
              <FormLabel required>{t("academics.periodOrder", "Numeric Order")}</FormLabel>
              <Input type="number" value={editPOrder} onChange={(e) => setEditPOrder(Number(e.target.value))} required />
            </FormField>
            <Button type="submit" disabled={submitting} className="w-full">
              {t("common.save", "Save Changes")}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Period Confirm Dialog */}
      <ConfirmDialog
        open={!!deletePeriodTarget}
        onOpenChange={(open) => !open && setDeletePeriodTarget(null)}
        title={t("academics.deletePeriodTitle", "Delete Period Slot")}
        description={t(
          "academics.deletePeriodConfirm",
          `Are you sure you want to delete "${deletePeriodTarget?.name}"? Routine slots scheduled in this period will be affected.`
        )}
        confirmLabel={t("common.delete", "Delete")}
        destructive
        loading={submitting}
        onConfirm={() => void handleDeletePeriod()}
      />

      {/* New Room Dialog */}
      <Dialog open={openRoomModal} onOpenChange={setOpenRoomModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.newRoomTitle", "Register Room")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateRoom(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.roomNumber", "Room Number / Identifier")}</FormLabel>
              <Input value={rNumber} onChange={(e) => setRNumber(e.target.value)} required placeholder="e.g. Room 302 / Physics Lab" />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.capacity", "Capacity")}</FormLabel>
                <Input type="number" value={rCapacity} onChange={(e) => setRCapacity(Number(e.target.value))} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.roomType", "Room Type")}</FormLabel>
                <Input value={rType} onChange={(e) => setRType(e.target.value)} required placeholder="Classroom / Lab" />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.create", "Save Room")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Room Dialog */}
      <Dialog open={!!editingRoom} onOpenChange={(open) => !open && setEditingRoom(null)}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.editRoomTitle", "Edit Room")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdateRoom(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.roomNumber", "Room Number / Identifier")}</FormLabel>
              <Input value={editRNumber} onChange={(e) => setEditRNumber(e.target.value)} required />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("academics.capacity", "Capacity")}</FormLabel>
                <Input type="number" value={editRCapacity} onChange={(e) => setEditRCapacity(Number(e.target.value))} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("academics.roomType", "Room Type")}</FormLabel>
                <Input value={editRType} onChange={(e) => setEditRType(e.target.value)} required />
              </FormField>
            </div>
            <Button type="submit" disabled={submitting} className="w-full">
              {t("common.save", "Save Changes")}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Room Confirm Dialog */}
      <ConfirmDialog
        open={!!deleteRoomTarget}
        onOpenChange={(open) => !open && setDeleteRoomTarget(null)}
        title={t("academics.deleteRoomTitle", "Delete Room")}
        description={t(
          "academics.deleteRoomConfirm",
          `Are you sure you want to delete room "${deleteRoomTarget?.name}"?`
        )}
        confirmLabel={t("common.delete", "Delete")}
        destructive
        loading={submitting}
        onConfirm={() => void handleDeleteRoom()}
      />
    </div>
  );
}
