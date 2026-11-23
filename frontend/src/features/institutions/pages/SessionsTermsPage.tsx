import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Calendar, CheckCircle2, Lock, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { institutionApi, type AcademicSession, type Term } from "@/features/institutions/api/institutionApi";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";

export function SessionsTermsPage() {
  const { t } = useTranslation();
  const { fetchContext } = useAcademicContextStore();
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [terms, setTerms] = useState<Term[]>([]);
  const [selectedSession, setSelectedSession] = useState<string>("");

  // Modals
  const [openSessionModal, setOpenSessionModal] = useState(false);
  const [openEditSessionModal, setOpenEditSessionModal] = useState(false);
  const [openTermModal, setOpenTermModal] = useState(false);
  const [openEditTermModal, setOpenEditTermModal] = useState(false);

  // Actions state
  const [sessionToActivate, setSessionToActivate] = useState<string | null>(null);
  const [sessionToClose, setSessionToClose] = useState<string | null>(null);
  const [sessionToDelete, setSessionToDelete] = useState<AcademicSession | null>(null);
  const [termToDelete, setTermToDelete] = useState<Term | null>(null);

  // Form states - Create Session
  const [yearName, setYearName] = useState("");
  const [startDate, setStartDate] = useState("2026-01-01");
  const [endDate, setEndDate] = useState("2026-12-31");

  // Form states - Edit Session
  const [editingSession, setEditingSession] = useState<AcademicSession | null>(null);
  const [editYearName, setEditYearName] = useState("");
  const [editStartDate, setEditStartDate] = useState("");
  const [editEndDate, setEditEndDate] = useState("");

  // Form states - Term
  const [termName, setTermName] = useState("");
  const [termStart, setTermStart] = useState("");
  const [termEnd, setTermEnd] = useState("");

  // Form states - Edit Term
  const [editingTerm, setEditingTerm] = useState<Term | null>(null);
  const [editTermName, setEditTermName] = useState("");
  const [editTermStart, setEditTermStart] = useState("");
  const [editTermEnd, setEditTermEnd] = useState("");

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
      void fetchContext(true);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.sessionCreateError", "Failed to create session.");
      toast.error(msg);
    }
  };

  const handleOpenEditSession = (s: AcademicSession) => {
    setEditingSession(s);
    setEditYearName(s.name);
    setEditStartDate(s.start_date);
    setEditEndDate(s.end_date);
    setOpenEditSessionModal(true);
  };

  const handleUpdateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSession) return;
    try {
      await institutionApi.updateSession(editingSession.id, {
        name: editYearName,
        start_date: editStartDate,
        end_date: editEndDate,
      });
      toast.success(t("institution.sessionUpdated", "Academic session updated."));
      setOpenEditSessionModal(false);
      setEditingSession(null);
      void loadData();
      void fetchContext(true);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.sessionUpdateError", "Failed to update session.");
      toast.error(msg);
    }
  };

  const handleDeleteSession = async () => {
    if (!sessionToDelete) return;
    if (sessionToDelete.is_current) {
      toast.error(t("institution.cannotDeleteActiveSession", "Cannot delete the active academic session. Activate another session first."));
      setSessionToDelete(null);
      return;
    }
    try {
      await institutionApi.deleteSession(sessionToDelete.id);
      toast.success(t("institution.sessionDeleted", "Academic session removed (soft deleted)."));
      setSessions((prev) => prev.filter((s) => s.id !== sessionToDelete.id));
      if (selectedSession === sessionToDelete.id) {
        setSelectedSession("");
      }
      void loadData();
      void fetchContext(true);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.sessionDeleteError", "Failed to delete session.");
      toast.error(msg);
    } finally {
      setSessionToDelete(null);
    }
  };

  const handleActivateSession = async () => {
    if (!sessionToActivate) return;
    try {
      await institutionApi.activateSession(sessionToActivate);
      toast.success(t("institution.sessionActivated", "Academic session is now active across the system."));
      void loadData();
      void fetchContext(true);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.sessionActivateError", "Failed to activate session.");
      toast.error(msg);
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
      void fetchContext(true);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.sessionCloseError", "Failed to close session.");
      toast.error(msg);
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
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.termCreateError", "Failed to create term.");
      toast.error(msg);
    }
  };

  const handleOpenEditTerm = (term: Term) => {
    setEditingTerm(term);
    setEditTermName(term.name);
    setEditTermStart(term.start_date);
    setEditTermEnd(term.end_date);
    setOpenEditTermModal(true);
  };

  const handleUpdateTerm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTerm) return;
    try {
      await institutionApi.updateTerm(editingTerm.id, {
        name: editTermName,
        start_date: editTermStart,
        end_date: editTermEnd,
      });
      toast.success(t("institution.termUpdated", "Academic term updated."));
      setOpenEditTermModal(false);
      setEditingTerm(null);
      void institutionApi.getTerms(selectedSession).then(setTerms);
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.termUpdateError", "Failed to update term.");
      toast.error(msg);
    }
  };

  const handleDeleteTerm = async () => {
    if (!termToDelete) return;
    try {
      await institutionApi.deleteTerm(termToDelete.id);
      toast.success(t("institution.termDeleted", "Term removed."));
      setTerms((prev) => prev.filter((t) => t.id !== termToDelete.id));
    } catch (err: unknown) {
      const msg = (err as Error)?.message || t("institution.termDeleteError", "Failed to delete term.");
      toast.error(msg);
    } finally {
      setTermToDelete(null);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("institution.sessionsTermsTitle", "Academic Sessions & Evaluation Terms")}
        subtitle={t("institution.sessionsTermsSubtitle", "Control annual calendar sessions, set active operational year, and manage evaluation terms.")}
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
              {t("institution.addSession", "New Session")}
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
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-xs text-ink">{s.name}</p>
                    {s.is_current && (
                      <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600">
                        <CheckCircle2 className="h-3 w-3" />
                        {t("institution.currentSession", "Active")}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-ink-muted hover:text-primary"
                      title={t("common.edit", "Edit Session")}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenEditSession(s);
                      }}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-ink-muted hover:text-danger"
                      title={t("common.delete", "Delete Session")}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSessionToDelete(s);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                <p className="mt-1 text-[11px] text-ink-muted font-mono">
                  {s.start_date} – {s.end_date}
                </p>

                <div className="mt-2.5 flex items-center justify-between gap-2 border-t border-border/50 pt-2">
                  {!s.is_current ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 text-[10px] px-2 font-medium"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSessionToActivate(s.id);
                      }}
                    >
                      <CheckCircle2 className="h-3 w-3 mr-1 text-emerald-600" />
                      {t("institution.activate", "Set Active")}
                    </Button>
                  ) : (
                    <span className="text-[10px] text-emerald-600 font-medium">
                      {t("institution.activeSystemWide", "Current Operational Session")}
                    </span>
                  )}

                  {s.is_current && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-[10px] text-ink-muted hover:text-danger px-1.5"
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
                {sessions.find((s) => s.id === selectedSession)?.name || t("institution.selectSessionPlaceholder", "Select a session")}
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
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-ink-muted hover:text-primary"
                        title={t("common.edit", "Edit Term")}
                        onClick={() => handleOpenEditTerm(term)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-danger hover:text-danger"
                        title={t("common.delete", "Delete Term")}
                        onClick={() => setTermToDelete(term)}
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
              <Input value={yearName} onChange={(e) => setYearName(e.target.value)} required placeholder="e.g. 2026 or 2026-2027" />
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

      {/* Edit Session Dialog */}
      <Dialog open={openEditSessionModal} onOpenChange={setOpenEditSessionModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("institution.editSessionTitle", "Edit Academic Session")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdateSession(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("institution.sessionName", "Session Name")}</FormLabel>
              <Input value={editYearName} onChange={(e) => setEditYearName(e.target.value)} required />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("institution.startDate", "Start Date")}</FormLabel>
                <Input type="date" value={editStartDate} onChange={(e) => setEditStartDate(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("institution.endDate", "End Date")}</FormLabel>
                <Input type="date" value={editEndDate} onChange={(e) => setEditEndDate(e.target.value)} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.saveChanges", "Save Changes")}</Button>
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

      {/* Edit Term Dialog */}
      <Dialog open={openEditTermModal} onOpenChange={setOpenEditTermModal}>
        <DialogContent closeLabel={t("common.close", "Close")}>
          <DialogHeader>
            <DialogTitle>{t("institution.editTermTitle", "Edit Academic Term")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => void handleUpdateTerm(e)} className="space-y-3 pt-2">
            <FormField>
              <FormLabel required>{t("institution.termName", "Term Name")}</FormLabel>
              <Input value={editTermName} onChange={(e) => setEditTermName(e.target.value)} required />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel required>{t("institution.startDate", "Start Date")}</FormLabel>
                <Input type="date" value={editTermStart} onChange={(e) => setEditTermStart(e.target.value)} required />
              </FormField>
              <FormField>
                <FormLabel required>{t("institution.endDate", "End Date")}</FormLabel>
                <Input type="date" value={editTermEnd} onChange={(e) => setEditTermEnd(e.target.value)} required />
              </FormField>
            </div>
            <Button type="submit" className="w-full">{t("common.saveChanges", "Save Changes")}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Session Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(sessionToDelete)}
        onOpenChange={(open) => { if (!open) setSessionToDelete(null); }}
        title={t("institution.deleteSessionTitle", "Delete Academic Session?")}
        description={t(
          "institution.deleteSessionDesc",
          `Are you sure you want to remove the "${sessionToDelete?.name}" session? It will be soft-deleted and preserved in archive records.`
        )}
        impactSummary={
          sessionToDelete?.is_current
            ? t("institution.deleteActiveSessionWarning", "Warning: Active sessions cannot be deleted. You must activate another session first.")
            : t("institution.deleteSessionImpact", "Any sections or schedules associated with this session will remain archived.")
        }
        confirmLabel={t("common.delete", "Delete Session")}
        destructive
        onConfirm={() => void handleDeleteSession()}
      />

      {/* Delete Term Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(termToDelete)}
        onOpenChange={(open) => { if (!open) setTermToDelete(null); }}
        title={t("institution.deleteTermTitle", "Delete Academic Term?")}
        description={t("institution.deleteTermDesc", `Are you sure you want to remove the term "${termToDelete?.name}"?`)}
        confirmLabel={t("common.delete", "Delete Term")}
        destructive
        onConfirm={() => void handleDeleteTerm()}
      />

      {/* Activation Confirm Dialog */}
      <ConfirmDialog
        open={Boolean(sessionToActivate)}
        onOpenChange={(open) => { if (!open) setSessionToActivate(null); }}
        title={t("institution.activateSessionTitle", "Activate Academic Session?")}
        description={t("institution.activateSessionDesc", "Activating this session will make it the default active academic session for all class rosters, chat history, attendance, exams, and routines system-wide.")}
        impactSummary={t("institution.activateSessionImpact", "Exactly 1 session can be active at a time. Any previously active session will be marked inactive.")}
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
