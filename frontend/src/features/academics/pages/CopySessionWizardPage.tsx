import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { ArrowRight, CheckCircle2, Copy, FileText, Info } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormLabel } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { institutionApi, type AcademicSession } from "@/features/institutions/api/institutionApi";
import { academicApi, type CopySessionResult } from "@/features/academics/api/academicApi";

export function CopySessionWizardPage() {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [isRunning, setIsRunning] = useState(false);
  const [previewResult, setPreviewResult] = useState<CopySessionResult | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await institutionApi.getSessions();
        setSessions(data);
        if (data.length >= 2 && data[0] && data[1]) {
          setSourceId(data[1].id);
          setTargetId(data[0].id);
        }
      } catch {
        toast.error(t("academics.loadSessionsError", "Failed to load sessions."));
      }
    }
    void load();
  }, [t]);

  const handleDryRun = async () => {
    if (!sourceId || !targetId || sourceId === targetId) {
      toast.error(t("academics.chooseDistinctSessions", "Select two distinct sessions."));
      return;
    }

    setIsRunning(true);
    try {
      const res = await academicApi.copySession({
        source_session_id: sourceId,
        target_session_id: targetId,
        dry_run: true,
      });
      setPreviewResult(res);
      setStep(2);
      toast.info(t("academics.dryRunSuccess", "Simulation completed. Review below."));
    } catch {
      toast.error(t("academics.dryRunError", "Failed to simulate session copy."));
    } finally {
      setIsRunning(false);
    }
  };

  const handleCommit = async () => {
    setIsRunning(true);
    try {
      const res = await academicApi.copySession({
        source_session_id: sourceId,
        target_session_id: targetId,
        dry_run: false,
      });
      setPreviewResult(res);
      setStep(3);
      toast.success(t("academics.copySessionSuccess", "Academic structure copied successfully."));
    } catch {
      toast.error(t("academics.copySessionError", "Failed to execute session rollover."));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("academics.copySessionWizardTitle", "Session Rollover & Structure Replication Wizard")}
        subtitle={t("academics.copySessionWizardSubtitle", "Idempotently copy sections, classes, and curriculum subject mappings across academic years.")}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Copy className="h-4 w-4 text-primary" />
              {step === 1 && t("academics.step1Title", "Step 1: Select Source and Destination Sessions")}
              {step === 2 && t("academics.step2Title", "Step 2: Dry-Run Simulation Preview")}
              {step === 3 && t("academics.step3Title", "Step 3: Rollover Completed")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {step === 1 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField>
                    <FormLabel required>{t("academics.sourceSession", "Source Session (Previous Year)")}</FormLabel>
                    <Select value={sourceId} onValueChange={setSourceId}>
                      <SelectTrigger><SelectValue placeholder="Choose source session..." /></SelectTrigger>
                      <SelectContent>
                        {sessions.map((s) => (
                          <SelectItem key={s.id} value={s.id}>{s.name} ({s.start_date})</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>

                  <FormField>
                    <FormLabel required>{t("academics.targetSession", "Target Session (New Year)")}</FormLabel>
                    <Select value={targetId} onValueChange={setTargetId}>
                      <SelectTrigger><SelectValue placeholder="Choose target session..." /></SelectTrigger>
                      <SelectContent>
                        {sessions.map((s) => (
                          <SelectItem key={s.id} value={s.id}>{s.name} ({s.start_date})</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                </div>

                <div className="rounded-md bg-canvas p-3 text-xs text-ink-muted flex items-start gap-2">
                  <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  <span>
                    The rollover will run in <strong>dry-run mode first</strong>. It will inspect all class levels, active sections, and class-subject offerings in the source session and simulate creating them in the target session, skipping any duplicates.
                  </span>
                </div>

                <Button onClick={() => void handleDryRun()} disabled={isRunning || !sourceId || !targetId || sourceId === targetId}>
                  {isRunning ? t("common.simulating", "Simulating...") : t("academics.startSimulation", "Simulate Rollover (Dry-Run)")}
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </div>
            )}

            {step === 2 && previewResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-md border border-border p-3 bg-canvas text-xs">
                    <p className="text-ink-muted">Sections</p>
                    <p className="mt-1 text-sm font-semibold text-ink">
                      <span className="text-emerald-600">+{previewResult.sections_created ?? 0}</span> to create
                    </p>
                    <p className="text-[11px] text-ink-muted font-mono mt-0.5">{previewResult.sections_skipped ?? 0} skipped (already exists)</p>
                  </div>
                  <div className="rounded-md border border-border p-3 bg-canvas text-xs">
                    <p className="text-ink-muted">Subject Offerings</p>
                    <p className="mt-1 text-sm font-semibold text-ink">
                      <span className="text-emerald-600">+{previewResult.class_subjects_created ?? 0}</span> to create
                    </p>
                    <p className="text-[11px] text-ink-muted font-mono mt-0.5">{previewResult.class_subjects_skipped ?? 0} skipped</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <Button variant="outline" size="sm" onClick={() => setStep(1)} disabled={isRunning}>
                    {t("common.back", "Back")}
                  </Button>
                  <Button size="sm" onClick={() => void handleCommit()} disabled={isRunning}>
                    {isRunning ? t("common.executing", "Executing...") : t("academics.confirmExecute", "Confirm & Execute Rollover")}
                  </Button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-3 py-4 text-center">
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 mb-2">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <h4 className="text-sm font-bold text-ink">{t("academics.rolloverDoneTitle", "Academic Structure Successfully Copied!")}</h4>
                <p className="text-xs text-ink-muted max-w-md mx-auto">
                  New sections and subject mappings are now registered for the target session. You can now build routines and promote students.
                </p>
                <div className="pt-2">
                  <Button size="sm" onClick={() => setStep(1)}>
                    {t("academics.startAnother", "Done")}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              {t("academics.annualProcess", "Annual Rollover Guide")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-ink-muted">
            <p>1. <strong>Session Creation:</strong> Ensure the new year session is created under Institutions &gt; Sessions.</p>
            <p>2. <strong>Structure Copy:</strong> Use this wizard to duplicate classes, section names, and subjects without manually re-entering them.</p>
            <p>3. <strong>Student Promotion:</strong> Run the promotion wizard in Task 06 to advance students from previous enrollments.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
