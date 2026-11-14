import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Clock, GitBranch, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { institutionApi, type Branch, type Shift } from "@/features/institutions/api/institutionApi";

export function BranchesShiftsPage() {
  const { t } = useTranslation();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [openBranchModal, setOpenBranchModal] = useState(false);
  const [openShiftModal, setOpenShiftModal] = useState(false);

  const [bName, setBName] = useState("");
  const [bCode, setBCode] = useState("");
  const [sName, setSName] = useState("");
  const [sStart, setSStart] = useState("08:00");
  const [sEnd, setSEnd] = useState("13:00");

  const loadData = useCallback(async () => {
    try {
      const [b, s] = await Promise.all([institutionApi.getBranches(), institutionApi.getShifts()]);
      setBranches(b);
      setShifts(s);
    } catch {
      toast.error(t("institution.loadBranchesError", "Failed to load branches and shifts."));
    }
  }, [t]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCreateBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await institutionApi.createBranch({ name: bName, code: bCode });
      toast.success(t("institution.branchCreated", "Branch created successfully."));
      setOpenBranchModal(false);
      setBName("");
      setBCode("");
      void loadData();
    } catch {
      toast.error(t("institution.branchCreateError", "Failed to create branch."));
    }
  };

  const handleCreateShift = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await institutionApi.createShift({ name: sName, start_time: sStart, end_time: sEnd });
      toast.success(t("institution.shiftCreated", "Shift created successfully."));
      setOpenShiftModal(false);
      setSName("");
      void loadData();
    } catch {
      toast.error(t("institution.shiftCreateError", "Failed to create shift."));
    }
  };

  const handleDeleteBranch = async (id: string) => {
    try {
      await institutionApi.deleteBranch(id);
      toast.success(t("institution.branchDeleted", "Branch removed."));
      void loadData();
    } catch {
      toast.error(t("institution.branchDeleteError", "Failed to delete branch."));
    }
  };

  const handleDeleteShift = async (id: string) => {
    try {
      await institutionApi.deleteShift(id);
      toast.success(t("institution.shiftDeleted", "Shift removed."));
      void loadData();
    } catch {
      toast.error(t("institution.shiftDeleteError", "Failed to delete shift."));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("institution.branchesShiftsTitle", "Branches & Operating Shifts")}
        subtitle={t("institution.branchesShiftsSubtitle", "Manage campus locations, geofence coordinates, and daily morning/day shifts.")}
      />

      <Tabs defaultValue="branches" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="branches" className="flex items-center gap-1.5">
            <GitBranch className="h-3.5 w-3.5" />
            {t("institution.branchesTab", "Campus Branches")}
          </TabsTrigger>
          <TabsTrigger value="shifts" className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            {t("institution.shiftsTab", "Daily Shifts")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="branches">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-semibold">{t("institution.branchesList", "Registered Branches")}</CardTitle>
              <Button size="sm" onClick={() => setOpenBranchModal(true)}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                {t("institution.addBranch", "Add Branch")}
              </Button>
            </CardHeader>
            <CardContent>
              {branches.length === 0 ? (
                <p className="text-xs text-ink-muted">{t("institution.noBranches", "No branches configured.")}</p>
              ) : (
                <div className="divide-y divide-border">
                  {branches.map((b) => (
                    <div key={b.id} className="flex items-center justify-between py-2.5 text-xs">
                      <div>
                        <p className="font-semibold text-ink">{b.name} <span className="font-mono text-ink-muted">({b.code})</span></p>
                        <p className="text-[11px] text-ink-muted">{b.address || t("institution.mainCampus", "Main Campus")}</p>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => void handleDeleteBranch(b.id)} className="text-danger hover:text-danger">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="shifts">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-semibold">{t("institution.shiftsList", "Shift Timings")}</CardTitle>
              <Button size="sm" onClick={() => setOpenShiftModal(true)}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                {t("institution.addShift", "Add Shift")}
              </Button>
            </CardHeader>
            <CardContent>
              {shifts.length === 0 ? (
                <p className="text-xs text-ink-muted">{t("institution.noShifts", "No shifts configured.")}</p>
              ) : (
                <div className="divide-y divide-border">
                  {shifts.map((s) => (
                    <div key={s.id} className="flex items-center justify-between py-2.5 text-xs">
                      <div>
                        <p className="font-semibold text-ink">{s.name}</p>
                        <p className="text-[11px] text-ink-muted font-mono">{s.start_time} – {s.end_time}</p>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => void handleDeleteShift(s.id)} className="text-danger hover:text-danger">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add Branch Modal */}
      <Dialog open={openBranchModal} onOpenChange={setOpenBranchModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("institution.newBranch", "New Campus Branch")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateBranch(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("institution.branchName", "Branch Name")}</FormLabel>
              <Input value={bName} onChange={(e) => setBName(e.target.value)} required placeholder="e.g. Uttara Campus" />
            </FormField>
            <FormField>
              <FormLabel required>{t("institution.branchCode", "Branch Code")}</FormLabel>
              <Input value={bCode} onChange={(e) => setBCode(e.target.value)} required placeholder="e.g. UTTARA" />
            </FormField>
            <Button type="submit" className="w-full">{t("common.create", "Create Branch")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add Shift Modal */}
      <Dialog open={openShiftModal} onOpenChange={setOpenShiftModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("institution.newShift", "New Operating Shift")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateShift(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("institution.shiftName", "Shift Name")}</FormLabel>
              <Input value={sName} onChange={(e) => setSName(e.target.value)} required placeholder="e.g. Morning Shift" />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("institution.startTime", "Start Time")}</FormLabel>
                <Input type="time" value={sStart} onChange={(e) => setSStart(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("institution.endTime", "End Time")}</FormLabel>
                <Input type="time" value={sEnd} onChange={(e) => setSEnd(e.target.value)} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.create", "Create Shift")}</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
