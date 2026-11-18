import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Clock, DoorOpen, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
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

  const [pName, setPName] = useState("");
  const [pStart, setPStart] = useState("08:00");
  const [pEnd, setPEnd] = useState("08:45");
  const [pOrder, setPOrder] = useState(1);

  const [rNumber, setRNumber] = useState("");
  const [rCapacity, setRCapacity] = useState(50);
  const [rType, setRType] = useState("classroom");

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
                    <div key={r.id} className="rounded-md border border-border bg-canvas p-3 text-xs">
                      <p className="font-semibold text-sm text-ink">{r.name}</p>
                      <p className="text-[11px] text-ink-muted">Type: {r.type_display || r.type || "General"}</p>
                      <p className="text-[11px] text-ink-muted">Capacity: {r.capacity} seats</p>
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
    </div>
  );
}
