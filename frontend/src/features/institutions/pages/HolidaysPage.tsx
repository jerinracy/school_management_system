import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { CalendarDays, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDate } from "@/lib/format";
import { institutionApi, type Holiday } from "@/features/institutions/api/institutionApi";

export function HolidaysPage() {
  const { t, i18n } = useTranslation();
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [openModal, setOpenModal] = useState(false);

  const [name, setName] = useState("");
  const [hType, setHType] = useState("govt");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const loadData = useCallback(async () => {
    try {
      const data = await institutionApi.getHolidays();
      setHolidays(data);
    } catch {
      toast.error(t("institution.loadHolidaysError", "Failed to load holidays."));
    }
  }, [t]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await institutionApi.createHoliday({
        name,
        type: hType,
        start_date: start,
        end_date: end || start,
      });
      toast.success(t("institution.holidayCreated", "Holiday added."));
      setOpenModal(false);
      setName("");
      void loadData();
    } catch {
      toast.error(t("institution.holidayCreateError", "Failed to add holiday."));
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await institutionApi.deleteHoliday(id);
      toast.success(t("institution.holidayDeleted", "Holiday removed."));
      setHolidays((prev) => prev.filter((h) => h.id !== id));
    } catch {
      toast.error(t("institution.holidayDeleteError", "Failed to delete holiday."));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("institution.holidaysTitle", "Official Holidays & Academic Recesses")}
        subtitle={t("institution.holidaysSubtitle", "Configure government, religious, and institutional holidays to bypass daily attendance rules.")}
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-primary" />
            {t("institution.holidaysList", "Annual Holidays Calendar")}
          </CardTitle>
          <Button size="sm" onClick={() => setOpenModal(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            {t("institution.addHoliday", "Add Holiday")}
          </Button>
        </CardHeader>
        <CardContent>
          {holidays.length === 0 ? (
            <p className="text-xs text-ink-muted">{t("institution.noHolidays", "No holidays registered.")}</p>
          ) : (
            <div className="divide-y divide-border">
              {holidays.map((h) => (
                <div key={h.id} className="flex items-center justify-between py-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-ink">
                      {h.name}
                      <span className="ml-2 inline-flex items-center rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary capitalize">
                        {h.type}
                      </span>
                    </p>
                    <p className="text-[11px] text-ink-muted font-mono">
                      {formatDate(h.start_date, i18n.language)} {h.end_date && h.end_date !== h.start_date ? `– ${formatDate(h.end_date, i18n.language)}` : ""}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => void handleDelete(h.id)} className="text-danger hover:text-danger">
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={openModal} onOpenChange={setOpenModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("institution.newHoliday", "Add Holiday or Vacation")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreate(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("institution.holidayName", "Holiday Name")}</FormLabel>
              <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Eid-ul-Fitr Vacation" />
            </FormField>
            <FormField>
              <FormLabel required>{t("institution.holidayType", "Holiday Type")}</FormLabel>
              <Select value={hType} onValueChange={setHType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="govt">Government Holiday</SelectItem>
                  <SelectItem value="religious">Religious Holiday</SelectItem>
                  <SelectItem value="institutional">Institutional / Discretionary</SelectItem>
                  <SelectItem value="emergency">Emergency Closure</SelectItem>
                </SelectContent>
              </Select>
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("institution.startDate", "Start Date")}</FormLabel>
                <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel>{t("institution.endDate", "End Date (Optional)")}</FormLabel>
                <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.create", "Save Holiday")}</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
