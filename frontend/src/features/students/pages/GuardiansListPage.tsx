import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  KeyRound,
  Plus,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import { studentsApi, type GuardianItem } from "@/features/students/api/studentsApi";
import { Can } from "@/features/auth/permissions";

export function GuardiansListPage() {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // New Guardian Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [nameEn, setNameEn] = useState("");
  const [nameBn, setNameBn] = useState("");
  const [phone, setPhone] = useState("");
  const [nid, setNid] = useState("");
  const [occupation, setOccupation] = useState("");
  const [modalError, setModalError] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["guardians", { search, page }],
    queryFn: () => studentsApi.getGuardians({ search: search || undefined, page }),
  });

  const guardians: GuardianItem[] = data?.results ?? [];
  const totalCount = data?.count ?? 0;

  const createGuardianMutation = useMutation({
    mutationFn: () =>
      studentsApi.createGuardian({
        name_en: nameEn,
        name_bn: nameBn,
        phone,
        nid: nid || undefined,
        occupation: occupation || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["guardians"] });
      setIsModalOpen(false);
      setNameEn("");
      setNameBn("");
      setPhone("");
      setNid("");
      setOccupation("");
      setModalError(null);
    },
    onError: (err: unknown) => {
      setModalError((err as Error).message || "Failed to create guardian.");
    },
  });

  const portalAccountMutation = useMutation({
    mutationFn: (guardianId: string) =>
      studentsApi.createGuardianPortalAccount(guardianId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["guardians"] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Return & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("students.guardiansDirectory", "Guardians Directory")}
            </h1>
            <span className="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 text-xs font-bold text-slate-700 dark:text-slate-300">
              {totalCount} {t("students.guardiansTotal", "Guardians")}
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-500">
            {t("students.guardiansSubtitle", "Household contacts, emergency contacts, and parent portal access.")}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/students"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 rounded-lg shadow-2xs"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>{t("students.backToDirectory", "Student Directory")}</span>
          </Link>

          <Can perm="students.manage">
            <Button
              size="sm"
              onClick={() => setIsModalOpen(true)}
              className="gap-1.5 text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>{t("students.newGuardian", "Add Guardian")}</span>
            </Button>
          </Can>
        </div>
      </div>

      {/* Search Bar */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5 shadow-2xs">
        <div className="relative max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("students.searchGuardians", "Search by name or mobile number...")}
            className="h-9 pl-9 text-xs rounded-lg border-slate-200 dark:border-slate-800"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">{t("students.guardian", "Guardian Name")}</th>
              <th className="px-4 py-3">{t("students.phone", "Mobile Number")}</th>
              <th className="px-4 py-3">{t("students.nid", "NID Number")}</th>
              <th className="px-4 py-3">{t("students.occupation", "Occupation")}</th>
              <th className="px-4 py-3 text-right">{t("common.actions", "Actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-400">
                  <div className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                    <span>{t("common.loading", "Loading guardians...")}</span>
                  </div>
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-danger">
                  <div className="flex flex-col items-center gap-2">
                    <span>{t("common.errorLoading", "Failed to load guardians.")}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        void refetch();
                      }}
                      className="text-xs"
                    >
                      {t("common.retry", "Retry")}
                    </Button>
                  </div>
                </td>
              </tr>
            ) : guardians.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-16 text-center text-slate-400">
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                    {t("students.noGuardians", "No guardians registered yet.")}
                  </p>
                </td>
              </tr>
            ) : (
              guardians.map((g) => (
                <tr key={g.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {currentLang === "bn" && g.name_bn ? g.name_bn : g.name_en}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono font-medium text-slate-700 dark:text-slate-300">
                    {g.phone}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-500">
                    {g.nid || "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                    {g.occupation || "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Can perm="students.manage">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => portalAccountMutation.mutate(g.id)}
                        disabled={portalAccountMutation.isPending}
                        className="h-8 gap-1 text-xs text-emerald-800 dark:text-emerald-400 hover:bg-emerald-50"
                      >
                        <KeyRound className="h-3.5 w-3.5" />
                        <span>{t("students.portalAccount", "Portal Access")}</span>
                      </Button>
                    </Can>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalCount > 20 && (
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{t("common.total", "Total")}: {totalCount}</span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="text-xs"
            >
              {t("common.previous", "Previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page * 20 >= totalCount}
              onClick={() => setPage((p) => p + 1)}
              className="text-xs"
            >
              {t("common.next", "Next")}
            </Button>
          </div>
        </div>
      )}

      {/* Add Guardian Dialog */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100">
              {t("students.addGuardian", "Add Guardian Record")}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              {t("students.addGuardianSubtitle", "Enter guardian demographics to link with student profiles.")}
            </DialogDescription>
          </DialogHeader>

          {modalError && (
            <div className="rounded-lg border border-danger/20 bg-danger/10 p-2.5 text-xs text-danger font-medium">
              {modalError}
            </div>
          )}

          <div className="space-y-3.5 py-2">
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.nameEn", "Full Name (English)")}
              </FormLabel>
              <Input
                value={nameEn}
                onChange={(e) => setNameEn(e.target.value)}
                placeholder="e.g. Rafiqul Islam"
                className="h-9 text-xs rounded-lg"
              />
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.nameBn", "Full Name (Bangla)")}
              </FormLabel>
              <Input
                value={nameBn}
                onChange={(e) => setNameBn(e.target.value)}
                placeholder="e.g. রফিকুল ইসলাম"
                className="h-9 text-xs rounded-lg"
              />
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.phone", "Mobile Number")}
              </FormLabel>
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+8801XXXXXXXXX"
                className="h-9 text-xs font-mono rounded-lg"
              />
            </FormField>

            <FormField>
              <FormLabel className="text-xs font-medium text-slate-700">
                {t("students.nid", "NID Number")}
              </FormLabel>
              <Input
                value={nid}
                onChange={(e) => setNid(e.target.value)}
                placeholder="e.g. 1985123456789"
                className="h-9 text-xs font-mono rounded-lg"
              />
            </FormField>

            <FormField>
              <FormLabel className="text-xs font-medium text-slate-700">
                {t("students.occupation", "Occupation")}
              </FormLabel>
              <Input
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
                placeholder="e.g. Government Service, Business, Teacher"
                className="h-9 text-xs rounded-lg"
              />
            </FormField>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
              className="text-xs rounded-lg"
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              size="sm"
              onClick={() => createGuardianMutation.mutate()}
              disabled={createGuardianMutation.isPending || !nameEn || !nameBn || !phone}
              className="text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
            >
              {createGuardianMutation.isPending
                ? t("common.saving", "Saving...")
                : t("common.save", "Save Guardian")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
