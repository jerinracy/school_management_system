import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { CheckCircle2, ChevronDown, ChevronRight, ChevronUp, Circle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toLocaleDigits } from "@/lib/format";

export interface SetupStep {
  id: string;
  titleKey: string;
  defaultTitle: string;
  descKey: string;
  defaultDesc: string;
  to: string;
  isComplete: boolean;
}

interface SetupProgressCardProps {
  defaultExpanded?: boolean;
}

export function SetupProgressCard({ defaultExpanded = false }: SetupProgressCardProps) {
  const { t, i18n } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const steps: SetupStep[] = [
    {
      id: "profile",
      titleKey: "setup.profile",
      defaultTitle: "Institution Profile & EIIN",
      descKey: "setup.profileDesc",
      defaultDesc: "Upload logo and configure basic school identifiers",
      to: "/institution/profile",
      isComplete: true,
    },
    {
      id: "branches_shifts",
      titleKey: "setup.branches",
      defaultTitle: "Campus Branches & Operating Shifts",
      descKey: "setup.branchesDesc",
      defaultDesc: "Define campuses and morning/day shift hours",
      to: "/institution/branches",
      isComplete: true,
    },
    {
      id: "sessions_terms",
      titleKey: "setup.sessions",
      defaultTitle: "Academic Sessions & Evaluation Terms",
      descKey: "setup.sessionsDesc",
      defaultDesc: "Set active academic year and term periods",
      to: "/institution/sessions",
      isComplete: true,
    },
    {
      id: "classes_sections",
      titleKey: "setup.classes",
      defaultTitle: "Classes, Sections & Subjects",
      descKey: "setup.classesDesc",
      defaultDesc: "Catalog curriculum and batch generate sections",
      to: "/academics/classes",
      isComplete: true,
    },
    {
      id: "routine",
      titleKey: "setup.routine",
      defaultTitle: "Weekly Class Routine & Timetable",
      descKey: "setup.routineDesc",
      defaultDesc: "Build conflict-checked timetable grid",
      to: "/academics/routine",
      isComplete: false,
    },
  ];

  const completedCount = steps.filter((s) => s.isComplete).length;
  const progressPercent = Math.round((completedCount / steps.length) * 100);
  const lang = i18n.language;

  return (
    <Card className="border-border bg-surface transition-colors shadow-2xs">
      <CardHeader className="flex flex-row items-center justify-between py-2.5 px-4">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-canvas border border-border text-primary">
            <CheckCircle2 className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <CardTitle className="text-xs font-semibold text-ink">
                {t("setup.progressTitle", "Institution Setup Checklist")}
              </CardTitle>
              <span className="rounded bg-primary-soft px-1.5 py-0.5 text-[10px] font-medium text-primary tabular-nums">
                {toLocaleDigits(progressPercent, lang)}%
              </span>
            </div>
            <p className="text-[10px] text-ink-muted truncate tabular-nums">
              {toLocaleDigits(completedCount, lang)} {t("setup.of", "of")}{" "}
              {toLocaleDigits(steps.length, lang)} {t("setup.completed", "milestones completed")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden sm:block w-20 bg-border rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-primary h-full transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            aria-expanded={isExpanded}
            className="inline-flex items-center gap-1 rounded border border-border bg-surface px-2 py-1 text-[11px] font-medium text-ink transition-colors hover:bg-slate-50"
          >
            <span>{isExpanded ? t("setup.hideSteps", "Hide") : t("setup.viewSteps", "View Steps")}</span>
            {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-1 pb-3 px-4 border-t border-border/50">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 mt-2">
            {steps.map((st) => (
              <Link
                key={st.id}
                to={st.to}
                className="flex flex-col justify-between rounded-md border border-border/80 bg-surface p-2.5 hover:border-primary/50 transition-all hover:shadow-xs group"
              >
                <div>
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-ink mb-1">
                    {st.isComplete ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    ) : (
                      <Circle className="h-3.5 w-3.5 text-ink-subtle shrink-0" />
                    )}
                    <span className="truncate">{t(st.titleKey, st.defaultTitle)}</span>
                  </div>
                  <p className="text-[10px] text-ink-muted line-clamp-2 leading-tight">
                    {t(st.descKey, st.defaultDesc)}
                  </p>
                </div>

                <div className="mt-2 flex items-center text-[10px] font-medium text-primary group-hover:underline">
                  <span>{st.isComplete ? t("setup.review", "Review") : t("setup.configure", "Configure")}</span>
                  <ChevronRight className="h-3 w-3 ml-0.5" />
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
