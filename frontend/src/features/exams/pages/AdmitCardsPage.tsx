import { useState, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft,
  FileText,
  Printer,
  Search,
  UserCheck,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { examsApi, type AdmitCardItem } from "@/features/exams/api/examsApi";

export default function AdmitCardsPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const examParam = searchParams.get("exam") || "";
  const [selectedExam, setSelectedExam] = useState<string>(examParam);
  const [search, setSearch] = useState("");
  const [previewCard, setPreviewCard] = useState<AdmitCardItem | null>(null);

  // Queries
  const { data: examsData } = useQuery({
    queryKey: ["exams-list"],
    queryFn: () => examsApi.getExams(),
  });

  const { data: admitCardsData, isLoading } = useQuery({
    queryKey: ["admit-cards-list", selectedExam, search],
    queryFn: () =>
      examsApi.getAdmitCards({
        exam: selectedExam || undefined,
        search: search.trim() || undefined,
      }),
  });

  const exams = useMemo(() => examsData?.results ?? [], [examsData]);
  const admitCards = useMemo(() => admitCardsData?.results ?? [], [admitCardsData]);

  // Generate Mutation
  const generateMutation = useMutation({
    mutationFn: () => {
      if (!selectedExam) throw new Error("Please select an examination first.");
      return examsApi.generateAdmitCards(selectedExam);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admit-cards-list"] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/exams" className="text-slate-400 hover:text-slate-600">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("exams.admitCardsTitle", "Examination Admit Cards & Hall Passes")}
            </h1>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t("exams.admitCardsSubtitle", "Generate, preview, and print official candidate hall passes with exam timetables.")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            disabled={!selectedExam || generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
            className="h-9 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
          >
            <FileText className="h-3.5 w-3.5" />
            {generateMutation.isPending ? "Generating..." : "Generate All Admit Cards"}
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search candidate name or roll..."
            className="h-9 pl-9 text-xs"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label htmlFor="admit-card-exam-select" className="text-xs text-slate-500">Select Exam:</label>
          <select
            id="admit-card-exam-select"
            value={selectedExam}
            onChange={(e) => setSelectedExam(e.target.value)}
            className="h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="">All Examinations</option>
            {exams.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.name} ({ex.session_name})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Roster Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading admit cards...</div>
        ) : admitCards.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <FileText className="mx-auto mb-2 h-8 w-8 text-slate-300" />
            <p className="font-semibold text-slate-700 dark:text-slate-300">No admit cards found</p>
            <p className="mt-1 text-slate-400">Select an examination cycle and click &quot;Generate All Admit Cards&quot;.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-semibold">Candidate Student</th>
                  <th className="px-4 py-3 font-semibold">Student ID</th>
                  <th className="px-4 py-3 font-semibold">Admit Card No.</th>
                  <th className="px-4 py-3 font-semibold">Issue Date</th>
                  <th className="px-4 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {admitCards.map((card) => (
                  <tr key={card.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      {card.student_name_en || card.student_name_bn}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600 dark:text-slate-400">
                      {card.student_id}
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-emerald-800 dark:text-emerald-400">
                      {card.card_number}
                    </td>
                    <td className="px-4 py-3 text-slate-500">{card.issue_date || "Issued"}</td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPreviewCard(card)}
                        className="h-7 gap-1 px-2.5 text-xs text-emerald-800 border-emerald-300"
                      >
                        <Printer className="h-3 w-3" />
                        Print Pass
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Printable Admit Card Preview */}
      {previewCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800 print:hidden">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Official Admit Card / প্রবেশপত্র
              </h2>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={() => window.print()}
                  className="h-8 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
                >
                  <Printer className="h-3.5 w-3.5" />
                  Print (A4)
                </Button>
                <button
                  onClick={() => setPreviewCard(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Printable Pass Container */}
            <div className="rounded-xl border-2 border-slate-900/80 p-6 space-y-4 bg-white text-slate-900 font-sans print:border-none print:p-0">
              {/* Institution Header */}
              <div className="text-center border-b pb-3 border-slate-300">
                <div className="flex items-center justify-center gap-2 mb-1">
                  <div className="h-8 w-8 rounded-full bg-emerald-800 text-white flex items-center justify-center font-bold text-xs">
                    SMS
                  </div>
                  <h3 className="text-base font-extrabold uppercase tracking-wide">
                    Dhaka Model High School &amp; College
                  </h3>
                </div>
                <p className="text-[11px] text-slate-600">EIIN: 134567 &bull; Dhaka Education Board &bull; Bangladesh</p>
                <div className="mt-2 inline-block rounded-md border border-slate-800 bg-slate-100 px-3 py-1 text-xs font-bold uppercase tracking-wider">
                  Admit Card / প্রবেশপত্র
                </div>
              </div>

              {/* Student Demographics */}
              <div className="grid grid-cols-3 gap-3 text-xs border-b pb-3 border-slate-200">
                <div className="col-span-2 space-y-1.5">
                  <div>
                    <span className="text-slate-500">Student Name:</span>{" "}
                    <span className="font-bold text-slate-900">{previewCard.student_name_en || previewCard.student_name_bn}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Student ID:</span>{" "}
                    <span className="font-mono font-semibold">{previewCard.student_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Admit No:</span>{" "}
                    <span className="font-mono font-bold text-emerald-800">{previewCard.card_number}</span>
                  </div>
                </div>

                <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-md p-2 bg-slate-50 text-[10px] text-slate-400">
                  <UserCheck className="h-8 w-8 text-slate-300 mb-1" />
                  Candidate Photo
                </div>
              </div>

              {/* Instructions */}
              <div className="space-y-1 text-[10px] text-slate-600">
                <p className="font-bold text-slate-800">General Instructions:</p>
                <p>1. Candidates must arrive at the examination hall at least 15 minutes before commencement.</p>
                <p>2. Electronic gadgets, mobile phones, and non-approved calculators are strictly prohibited.</p>
                <p>3. This admit card must be produced to the invigilator during every examination session.</p>
              </div>

              {/* Signatures */}
              <div className="flex justify-between items-end pt-8 text-[11px] text-slate-700">
                <div className="text-center">
                  <div className="border-t border-slate-400 w-32 pt-1 font-semibold">Class Teacher</div>
                </div>
                <div className="text-center">
                  <div className="border-t border-slate-400 w-32 pt-1 font-semibold">Exam Controller</div>
                </div>
                <div className="text-center">
                  <div className="border-t border-slate-400 w-32 pt-1 font-semibold">Principal</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
