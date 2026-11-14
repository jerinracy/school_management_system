import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Calendar, CheckCircle2, Lock, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { institutionApi, type AcademicSession, type Term } from "@/features/institutions/api/institutionApi";

export function SessionsTermsPage() {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [terms, setTerms] = useState<Term[]>([]);
  const [selectedSession, setSelectedSession] = useState<string>("");

  const [openSessionModal, setOpenSessionModal] = useState(false);
  const [openTermModal, setOpenTermModal] = useState(false);
  const [sessionToActivate, setSessionToActivate] = useState<string | null>(null);
  const [sessionToClose, setSessionToClose] = useState<string | null>(null);

  const [yearName, setYearName] = useState("");
  const [startDate, setStartDate] = useState("2026-01-01");
  const [endDate, setEndDate] = useState("2026-12-31");

  const [termName, setTermName] = useState("");
  const [termStart, setTermStart] = useState("");
  const [termEnd, setTermEnd] = useState("");

  const loadData = useCallback(async () => {
    try {
      const sessList = await institutionApi.getSessions();
      setSessions(sessList);
      if (sessList.length > 0 && !selectedSession) {
        const active = sessList.find((s) => s.is_current) || sessList[0];
        if (active) {
          setSelectedSession(active.id);
        }
      }
    } catch {
      toast.error(t("institution.loadSessionsError", "Failed to load academic sessions."));
    }
  }, [t, selectedSession]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (selectedSession) {
      void institutionApi.getTerms(selectedSession).then(setTerms);
    }
  }, [selectedSession]);

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await institutionApi.createSession({
        name: yearName,
        start_date: startDate,
        end_date: endDate,
      });
      toast.success(t("institution.sessionCreated", "Academic session created."));
      setOpenSessionModal(false);
      setYearName("");
      void loadData();
    } catch {
      toast.error(t("institution.sessionCreateError", "Failed to create session."));
    }
  };

  const handleActivateSession = async () => {
    if (!sessionToActivate) return;
    try {
      await institutionApi.activateSession(sessionToActivate);
      toast.success(t("institution.sessionActivated", "Academic session is now active."));
      void loadData();
    } catch {
      toast.error(t("institution.sessionActivateError", "Failed to activate session."));
    } finally {
      setSessionToActivate(null);
    }
  };

  const handleCloseSession = async () => {
    if (!sessionToClose) return;
    try {
      await institutionApi.closeSession(sessionToClose);
      toast.success(t("institution.sessionClosed", "Academic session closed."));
      void loadData();
    } catch {
      toast.error(t("institution.sessionCloseError", "Failed to close session."));
    } finally {
      setSessionToClose(null);
    }
  };

  const handleCreateTerm = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await institutionApi.createTerm({
        session: selectedSession,
        name: termName,
        start_date: termStart,
        end_date: termEnd,
      });
      toast.success(t("institution.termCreated", "Academic term created."));
      setOpenTermModal(false);
      setTermName("");
      void institutionApi.getTerms(selectedSession).then(setTerms);
    } catch {
      toast.error(t("institution.termCreateError", "Failed to create term."));
    }
  };

  const handleDeleteTerm = async (id: string) => {
    try {
      await institutionApi.deleteTerm(id);
      toast.success(t("institution.termDeleted", "Term removed."));
      setTerms((prev) => prev.filter((t) => t.id !== id));
    } catch {
      toast.error(t("institution.termDeleteError", "Failed to delete term."));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("institution.sessionsTermsTitle", "Academic Sessions & Evaluation Terms")}
        subtitle={t("institution.sessionsTermsSubtitle", "Control annual calendar sessions, active term boundaries, and evaluation periods.")}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Sessions list */}
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Calendar className="h-4 w-4 text-primary" />
              {t("institution.sessionsList", "Academic Sessions")}
            </CardTitle>
            <Button size="sm" onClick={() => setOpenSessionModal(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              {t("institution.addSession", "New")}
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {sessions.map((s) => (
              <div
                key={s.id}
                role="button"
                tabIndex={0}
                onClick={() => setSelectedSession(s.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    setSelectedSession(s.id);
                  }
                }}
                className={`cursor-pointer rounded-md border p-3 transition-colors ${
                  selectedSession === s.id ? "border-primary bg-primary/5" : "border-border hover:bg-canvas"
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-xs text-ink">{s.name}</p>
                  {s.is_current ? (
                    <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" />
                      {t("institution.currentSession", "Active")}
                    </span>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 text-[10px] px-1.5"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSessionToActivate(s.id);
                      }}
                    >
                      {t("institution.activate", "Activate")}
                    </Button>
                  )}
                </div>
                <p className="mt-1 text-[11px] text-ink-muted font-mono">
                  {s.start_date} – {s.end_date}
                </p>
                {s.is_current && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 h-6 text-[10px] text-ink-muted hover:text-danger w-full justify-start"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSessionToClose(s.id);
                    }}
                  >
                    <Lock className="h-3 w-3 mr-1" />
                    {t("institution.closeSession", "Close Session")}
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Terms for selected session */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-sm font-semibold">
                {t("institution.termsList", "Evaluation Terms in Session")}
              </CardTitle>
              <p className="text-xs text-ink-muted">
                {sessions.find((s) => s.id === selectedSession)?.name || "Select a session"}
              </p>
            </div>
            <Button size="sm" onClick={() => setOpenTermModal(true)} disabled={!selectedSession}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              {t("institution.addTerm", "Add Term")}
            </Button>
          </CardHeader>
          <CardContent>
            {terms.length === 0 ? (
              <p className="text-xs text-ink-muted">{t("institution.noTerms", "No terms created for this session.")}</p>
            ) : (
              <div className="divide-y divide-border">
                {terms.map((term) => (
                  <div key={term.id} className="flex items-center justify-between py-2.5 text-xs">
                    <div>
                      <p className="font-semibold text-ink">{term.name}</p>
                      <p className="text-[11px] text-ink-muted font-mono">
                        {term.start_date} – {term.end_date}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void handleDeleteTerm(term.id)}
                      className="text-danger hover:text-danger"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* New Session Dialog */}
      <Dialog open={openSessionModal} onOpenChange={setOpenSessionModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("institution.newSessionTitle", "Create Academic Session")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateSession(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("institution.sessionName", "Session Name")}</FormLabel>
              <Input value={yearName} onChange={(e) => setYearName(e.target.value)} required placeholder="e.g. 2026" />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("institution.startDate", "Start Date")}</FormLabel>
                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("institution.endDate", "End Date")}</FormLabel>
                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.create", "Create Session")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* New Term Dialog */}
      <Dialog open={openTermModal} onOpenChange={setOpenTermModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("institution.newTermTitle", "Create Academic Term")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleCreateTerm(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("institution.termName", "Term Name")}</FormLabel>
              <Input value={termName} onChange={(e) => setTermName(e.target.value)} required placeholder="e.g. First Term / Half Yearly" />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("institution.startDate", "Start Date")}</FormLabel>
                <Input type="date" value={termStart} onChange={(e) => setTermStart(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("institution.endDate", "End Date")}</FormLabel>
                <Input type="date" value={termEnd} onChange={(e) => setTermEnd(e.target.value)} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.create", "Create Term")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Activation Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(sessionToActivate)}
        onOpenChange={(open) => { if (!open) setSessionToActivate(null); }}
        title={t("institution.activateSessionTitle", "Activate Academic Session?")}
        description={t("institution.activateSessionDesc", "Activating this session will make it the default academic session for student rosters, attendance, and routines.")}
        impactSummary={t("institution.activateSessionImpact", "Any previously active session will be marked inactive.")}
        confirmLabel={t("institution.activateConfirmBtn", "Activate Session")}
        onConfirm={() => void handleActivateSession()}
      />

      {/* Close Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(sessionToClose)}
        onOpenChange={(open) => { if (!open) setSessionToClose(null); }}
        title={t("institution.closeSessionTitle", "Close Academic Session?")}
        description={t("institution.closeSessionDesc", "Closing this session will mark all terms finalized and lock historical schedules.")}
        impactSummary={t("institution.closeSessionImpact", "Students should be promoted before or immediately after closing.")}
        confirmLabel={t("institution.closeConfirmBtn", "Close Session")}
        destructive
        onConfirm={() => void handleCloseSession()}
      />
    </div>
  );
}
