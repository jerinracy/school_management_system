import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Plus, UserCheck } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { formatDate } from "@/lib/format";
import { academicApi, type Substitute } from "@/features/academics/api/academicApi";

export function SubstitutesPage() {
  const { t, i18n } = useTranslation();
  const [substitutes, setSubstitutes] = useState<Substitute[]>([]);
  const [openModal, setOpenModal] = useState(false);

  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [reason, setReason] = useState("");

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

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await academicApi.createSubstitute({
        date,
        reason,
      });
      toast.success(t("academics.substituteCreated", "Substitute teacher assigned."));
      setOpenModal(false);
      setReason("");
      void loadData();
    } catch {
      toast.error(t("academics.substituteCreateError", "Failed to assign substitute."));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.substitutesTitle", "Teacher Substitutions & Cover Allocations")}
        subtitle={t("academics.substitutesSubtitle", "Assign substitute teachers to cover classes during faculty leave or absence.")}
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-primary" />
            {t("academics.substitutesList", "Active Cover Assignments")}
          </CardTitle>
          <Button size="sm" onClick={() => setOpenModal(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            {t("academics.addSubstitute", "Assign Cover")}
          </Button>
        </CardHeader>
        <CardContent>
          {substitutes.length === 0 ? (
            <p className="text-xs text-ink-muted">{t("academics.noSubstitutes", "No substitute teacher assignments recorded.")}</p>
          ) : (
            <div className="divide-y divide-border">
              {substitutes.map((sub) => (
                <div key={sub.id} className="flex items-center justify-between py-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-ink">
                      {sub.substitute_teacher_name || "Substitute Teacher"}
                      <span className="ml-2 text-ink-muted">covering for {sub.original_teacher_name || "Primary Teacher"}</span>
                    </p>
                    <p className="text-[11px] text-ink-muted">
                      {formatDate(sub.slot_date, i18n.language)} • Reason: {sub.reason || "Leave"}
                    </p>
                  </div>
                  <span className="inline-flex items-center rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-600">
                    Active
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={openModal} onOpenChange={setOpenModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("academics.newSubstituteTitle", "Assign Substitute Cover")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreate(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("academics.date", "Date")}</FormLabel>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            </FormField>
            <FormField>
              <FormLabel required>{t("academics.reason", "Reason for Substitution")}</FormLabel>
              <Input value={reason} onChange={(e) => setReason(e.target.value)} required placeholder="e.g. Medical Leave / Official Training" />
            </FormField>
            <Button type="submit" className="w-full">{t("common.create", "Assign Cover")}</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
