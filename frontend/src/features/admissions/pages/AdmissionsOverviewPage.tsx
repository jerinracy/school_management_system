import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dice5,
  Layers,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  admissionsApi,
  type CircularListItem,
  type ApplicationListItem,
} from "@/features/admissions/api/admissionsApi";
import { Can } from "@/features/auth/permissions";

export function AdmissionsOverviewPage() {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("circulars");

  // Circulars Query
  const { data: circularsData, isLoading: loadingCirculars } = useQuery({
    queryKey: ["admissions-circulars"],
    queryFn: () => admissionsApi.getCirculars(),
  });

  // Applications Query
  const { data: applicationsData, isLoading: loadingApplications } = useQuery({
    queryKey: ["admissions-applications"],
    queryFn: () => admissionsApi.getApplications(),
  });

  const circulars: CircularListItem[] = circularsData?.results ?? [];
  const applications: ApplicationListItem[] = applicationsData?.results ?? [];

  // Actions
  const publishMutation = useMutation({
    mutationFn: (id: string) => admissionsApi.publishCircular(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admissions-circulars"] });
    },
  });

  const closeMutation = useMutation({
    mutationFn: (id: string) => admissionsApi.closeCircular(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admissions-circulars"] });
    },
  });

  const lotteryMutation = useMutation({
    mutationFn: (circularId: string) => admissionsApi.runLotteryDraw({ circular_id: circularId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admissions-applications"] });
      void queryClient.invalidateQueries({ queryKey: ["admissions-circulars"] });
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "published":
      case "admitted":
        return (
          <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
            {status.toUpperCase()}
          </span>
        );
      case "draft":
      case "submitted":
        return (
          <span className="inline-flex items-center rounded-md bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60">
            {status.toUpperCase()}
          </span>
        );
      case "closed":
      case "rejected":
        return (
          <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
            {status.toUpperCase()}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-600">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {t("admissions.title", "Admissions Management")}
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-500">
            {t("admissions.subtitle", "Intake circulars, online candidate applications, lottery selection, and merit processing.")}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="mb-6 grid w-full max-w-xs grid-cols-2 rounded-xl bg-slate-100/90 dark:bg-slate-800/60 p-1 border border-slate-200/60">
          <TabsTrigger
            value="circulars"
            className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-slate-900 data-[state=active]:shadow-2xs text-slate-600 dark:text-slate-400"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>{t("admissions.tabCirculars", "Circulars")}</span>
          </TabsTrigger>
          <TabsTrigger
            value="applications"
            className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-slate-900 data-[state=active]:shadow-2xs text-slate-600 dark:text-slate-400"
          >
            <Users className="h-3.5 w-3.5" />
            <span>{t("admissions.tabApplications", "Applications")}</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Circulars */}
        <TabsContent value="circulars" className="space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3">{t("admissions.circularName", "Circular Name")}</th>
                  <th className="px-4 py-3">{t("admissions.classGrade", "Class Grade")}</th>
                  <th className="px-4 py-3">{t("admissions.applicationWindow", "Application Window")}</th>
                  <th className="px-4 py-3">{t("admissions.capacity", "Capacity / Seats")}</th>
                  <th className="px-4 py-3">{t("common.status", "Status")}</th>
                  <th className="px-4 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {loadingCirculars ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      <div className="inline-flex items-center gap-2">
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                        <span>{t("common.loading", "Loading circulars...")}</span>
                      </div>
                    </td>
                  </tr>
                ) : circulars.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-16 text-center text-slate-400">
                      <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        {t("admissions.noCirculars", "No admission circulars created yet.")}
                      </p>
                    </td>
                  </tr>
                ) : (
                  circulars.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        {c.title}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {c.class_level_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-mono">
                        {c.form_open_date} → {c.form_close_date}
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-slate-700 dark:text-slate-300">
                        {c.seats_available ?? 0} {t("admissions.seats", "seats")}
                      </td>
                      <td className="px-4 py-3">
                        {getStatusBadge(c.status ?? "draft")}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Can perm="admissions.manage">
                          <div className="inline-flex items-center gap-1.5">
                            {c.status === "draft" && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => publishMutation.mutate(c.id)}
                                disabled={publishMutation.isPending}
                                className="h-7 text-[11px] rounded"
                              >
                                {t("admissions.publish", "Publish")}
                              </Button>
                            )}
                            {c.status === "published" && (
                              <>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => lotteryMutation.mutate(c.id)}
                                  disabled={lotteryMutation.isPending}
                                  className="h-7 text-[11px] gap-1 rounded text-purple-700 border-purple-200 hover:bg-purple-50"
                                >
                                  <Dice5 className="h-3 w-3" />
                                  <span>{t("admissions.runLottery", "Draw Lottery")}</span>
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => closeMutation.mutate(c.id)}
                                  disabled={closeMutation.isPending}
                                  className="h-7 text-[11px] text-slate-500 hover:text-slate-800 rounded"
                                >
                                  {t("admissions.close", "Close")}
                                </Button>
                              </>
                            )}
                          </div>
                        </Can>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* Tab 2: Applications */}
        <TabsContent value="applications" className="space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3">{t("admissions.applicant", "Applicant Name")}</th>
                  <th className="px-4 py-3">{t("admissions.applicationNo", "Application No")}</th>
                  <th className="px-4 py-3">{t("admissions.phone", "Guardian Phone")}</th>
                  <th className="px-4 py-3">{t("admissions.circular", "Circular")}</th>
                  <th className="px-4 py-3">{t("common.status", "Status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {loadingApplications ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400">
                      <div className="inline-flex items-center gap-2">
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                        <span>{t("common.loading", "Loading applications...")}</span>
                      </div>
                    </td>
                  </tr>
                ) : applications.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-16 text-center text-slate-400">
                      <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        {t("admissions.noApplications", "No applications received yet.")}
                      </p>
                    </td>
                  </tr>
                ) : (
                  applications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        {currentLang === "bn" && app.name_bn ? app.name_bn : app.name_en}
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-emerald-800 dark:text-emerald-400">
                        {app.application_no}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                        {app.guardian_phone}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {app.class_level_name || "—"} ({app.session_name || "—"})
                      </td>
                      <td className="px-4 py-3">
                        {getStatusBadge(app.status ?? "submitted")}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
