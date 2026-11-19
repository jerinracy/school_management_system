import { Printer } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { useBrandingStore } from "@/features/institutions/store/brandingStore";
import type { ExamResultItem, SubjectResultItem } from "@/features/results/api/resultsApi";

interface ReportCardPreviewProps {
  result: ExamResultItem;
  subjectResults?: SubjectResultItem[];
  onClose?: () => void;
}

export function ReportCardPreview({ result, subjectResults = [], onClose }: ReportCardPreviewProps) {
  const { i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const { getLocalizedName, getEIIN, getBoard, getLogoUrl } = useBrandingStore();

  const schoolName = getLocalizedName(currentLang);
  const schoolEIIN = getEIIN();
  const schoolBoard = getBoard();
  const schoolLogo = getLogoUrl();

  return (
    <div className="space-y-4">
      {/* Action Bar */}
      <div className="flex items-center justify-between border-b pb-3 pr-8 print:hidden">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
          Official Academic Progress Report Card / অগ্রগতি পত্র
        </h3>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => window.print()}
            className="h-8 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
          >
            <Printer className="h-3.5 w-3.5" />
            Print Report Card (A4)
          </Button>
          {onClose && (
            <Button variant="outline" size="sm" onClick={onClose} className="h-8 text-xs">
              Close
            </Button>
          )}
        </div>
      </div>

      {/* Printable Sheet */}
      <div className="rounded-xl border-2 border-slate-900/80 p-8 space-y-6 bg-white text-slate-900 font-sans print:border-none print:p-0">
        {/* Institutional Header */}
        <div className="text-center border-b-2 border-slate-900 pb-4">
          <div className="flex items-center justify-center gap-2 mb-1">
            {schoolLogo ? (
              <img src={schoolLogo} alt={schoolName} className="h-10 w-10 object-contain rounded-full" />
            ) : (
              <div className="h-10 w-10 rounded-full bg-emerald-800 text-white flex items-center justify-center font-black text-sm">
                SMS
              </div>
            )}
            <h2 className="text-xl font-black uppercase tracking-wide">
              {schoolName}
            </h2>
          </div>
          <p className="text-xs text-slate-600 font-medium">
            EIIN: {schoolEIIN} &bull; {schoolBoard} Education Board &bull; Bangladesh
          </p>
          <div className="mt-2 inline-block rounded-md border border-slate-900 bg-slate-100 px-4 py-1 text-xs font-bold uppercase tracking-wider">
            Academic Progress Report / একাডেমিক ফলাফল
          </div>
        </div>

        {/* Candidate Information Card */}
        <div className="grid grid-cols-4 gap-4 text-xs border p-3 rounded-lg bg-slate-50/50">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Student Name</span>
            <span className="font-extrabold text-slate-900 text-sm">{result.student_name}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Student ID / Code</span>
            <span className="font-mono font-semibold">{result.student_code}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Class &amp; Section</span>
            <span className="font-bold">{result.class_level_name} ({result.section_name})</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Roll Number</span>
            <span className="font-mono font-extrabold text-emerald-800 text-sm">{result.roll_no}</span>
          </div>
        </div>

        {/* Subject-Wise Marks & Grades Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border border-collapse border-slate-300">
            <thead className="bg-slate-100 text-slate-800 font-bold border-b border-slate-300">
              <tr>
                <th className="p-2 border border-slate-300">Subject</th>
                <th className="p-2 border border-slate-300 text-center w-16">Full</th>
                <th className="p-2 border border-slate-300 text-center w-14">CQ</th>
                <th className="p-2 border border-slate-300 text-center w-14">MCQ</th>
                <th className="p-2 border border-slate-300 text-center w-14">PR</th>
                <th className="p-2 border border-slate-300 text-center w-16">Total</th>
                <th className="p-2 border border-slate-300 text-center w-14">Grade</th>
                <th className="p-2 border border-slate-300 text-center w-14">GP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {subjectResults.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-4 text-center text-slate-500">
                    Subject breakdown available on full tabulation export.
                  </td>
                </tr>
              ) : (
                subjectResults.map((sub) => (
                  <tr key={sub.id}>
                    <td className="p-2 border border-slate-300 font-semibold">
                      {sub.subject_name}{" "}
                      {sub.is_fourth_subject && <span className="text-[10px] text-emerald-700">(4th Subject)</span>}
                    </td>
                    <td className="p-2 border border-slate-300 text-center font-mono">{sub.full_marks}</td>
                    <td className="p-2 border border-slate-300 text-center font-mono">{sub.creative_marks ?? "-"}</td>
                    <td className="p-2 border border-slate-300 text-center font-mono">{sub.mcq_marks ?? "-"}</td>
                    <td className="p-2 border border-slate-300 text-center font-mono">{sub.practical_marks ?? "-"}</td>
                    <td className="p-2 border border-slate-300 text-center font-mono font-bold">{sub.total_marks}</td>
                    <td className="p-2 border border-slate-300 text-center font-bold">
                      <span className={sub.letter_grade === "A+" ? "text-emerald-800" : sub.letter_grade === "F" ? "text-rose-600" : ""}>
                        {sub.letter_grade}
                      </span>
                    </td>
                    <td className="p-2 border border-slate-300 text-center font-mono font-semibold">{sub.grade_point}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* GPA 5.0 Performance Summary & Grading Legend */}
        <div className="grid grid-cols-2 gap-4 text-xs">
          {/* Summary Banner */}
          <div className="rounded-lg border border-slate-300 p-4 space-y-2 bg-slate-50/50">
            <h4 className="font-bold text-slate-800 border-b pb-1">Performance Summary</h4>
            <div className="flex justify-between">
              <span className="text-slate-500">Total Marks Obtained:</span>
              <span className="font-mono font-bold text-slate-900">{result.total_marks || "0"} / {result.total_full_marks || "0"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">GPA (without 4th subject):</span>
              <span className="font-mono">{result.gpa_without_fourth || "0.00"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">4th Subject Bonus GP:</span>
              <span className="font-mono text-emerald-700 font-semibold">+{result.fourth_subject_bonus || "0.00"}</span>
            </div>
            <div className="flex justify-between border-t pt-1">
              <span className="font-bold text-slate-900">Final CGPA:</span>
              <span className="font-mono font-black text-base text-emerald-900">{result.final_gpa || "0.00"} / 5.00</span>
            </div>
            <div className="flex justify-between">
              <span className="font-bold text-slate-900">Final Letter Grade:</span>
              <span className="font-black text-sm text-emerald-900">{result.final_grade}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Merit Position:</span>
              <span className="font-bold">Class #{result.class_position} &bull; Section #{result.section_position}</span>
            </div>
          </div>

          {/* Grading Legend */}
          <div className="rounded-lg border border-slate-300 p-3 space-y-1.5 bg-slate-50/50">
            <h4 className="font-bold text-slate-800 border-b pb-1 text-[11px]">NCTB Grading Scale (GPA 5.0)</h4>
            <div className="grid grid-cols-3 gap-1 text-[10px] text-slate-600">
              <div>80-100%: <b>A+</b> (5.00)</div>
              <div>70-79%: <b>A</b> (4.00)</div>
              <div>60-69%: <b>A-</b> (3.50)</div>
              <div>50-59%: <b>B</b> (3.00)</div>
              <div>40-49%: <b>C</b> (2.00)</div>
              <div>33-39%: <b>D</b> (1.00)</div>
              <div className="col-span-3 text-rose-600 font-bold">0-32%: F (0.00) - Fail</div>
            </div>
          </div>
        </div>

        {/* Remarks & Signatures */}
        <div className="grid grid-cols-3 gap-4 pt-10 text-xs text-center border-t border-slate-300">
          <div>
            <div className="border-t border-slate-500 pt-1 font-semibold">Class Teacher</div>
          </div>
          <div>
            <div className="border-t border-slate-500 pt-1 font-semibold">Guardian Signature</div>
          </div>
          <div>
            <div className="border-t border-slate-500 pt-1 font-semibold">Principal / Headmaster</div>
          </div>
        </div>
      </div>
    </div>
  );
}
