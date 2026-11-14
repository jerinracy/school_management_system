import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { CheckCircle2, ChevronRight, Circle, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface SetupStep {
  id: string;
  titleKey: string;
  defaultTitle: string;
  descKey: string;
  defaultDesc: string;
  to: string;
  isComplete: boolean;
}

export function SetupProgressCard() {
  const { t } = useTranslation();

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
      isComplete: false,
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

  return (
    <Card className="border-primary/20 bg-gradient-to-r from-primary/5 via-surface to-surface">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-white">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <CardTitle className="text-sm font-semibold text-ink">
              {t("setup.progressTitle", "Institution Setup Checklist")}
            </CardTitle>
            <p className="text-[11px] text-ink-muted">
              {completedCount} of {steps.length} setup milestones completed ({progressPercent}%)
            </p>
          </div>
        </div>

        <div className="w-24 bg-border rounded-full h-2 overflow-hidden">
          <div
            className="bg-primary h-full transition-all duration-500 rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
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
    </Card>
  );
}
