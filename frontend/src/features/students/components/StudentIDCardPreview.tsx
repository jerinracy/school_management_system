import { useTranslation } from "react-i18next";
import { Download, Printer, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AcademicLogo } from "@/features/institutions/components/AcademicLogo";
import { useBrandingStore } from "@/features/institutions/store/brandingStore";
import type { StudentDetail } from "@/features/students/api/studentsApi";

interface StudentIDCardPreviewProps {
  student: StudentDetail;
  onDownloadPdf?: () => void;
}

export function StudentIDCardPreview({
  student,
  onDownloadPdf,
}: StudentIDCardPreviewProps) {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const { getLocalizedName, getLogoUrl, getEIIN } = useBrandingStore();

  const schoolName = getLocalizedName(currentLang);
  const logoUrl = getLogoUrl();
  const eiin = getEIIN();

  const activeEnrollment = student.enrollments?.[0];

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Top Action Bar */}
      <div className="flex items-center gap-3 w-full justify-between max-w-[480px]">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span>{t("students.officialCard", "Institutional Student Identity Card")}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrint}
            className="h-8 gap-1.5 text-xs rounded-lg"
          >
            <Printer className="h-3.5 w-3.5" />
            <span>{t("common.print", "Print")}</span>
          </Button>
          {onDownloadPdf && (
            <Button
              size="sm"
              onClick={onDownloadPdf}
              className="h-8 gap-1.5 text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg"
            >
              <Download className="h-3.5 w-3.5" />
              <span>{t("common.downloadPdf", "Download PDF")}</span>
            </Button>
          )}
        </div>
      </div>

      {/* ID Card Front Frame (Standard CR80 Ratio 85.6mm x 54mm) */}
      <div className="relative w-full max-w-[420px] aspect-[1.586] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-md overflow-hidden flex flex-col justify-between text-slate-900 dark:text-slate-100 font-sans print:shadow-none print:border">
        {/* Card Header */}
        <div className="bg-emerald-800 text-white px-4 py-2.5 flex items-center justify-between border-b border-emerald-900">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-white/10 p-1 flex items-center justify-center">
              <AcademicLogo
                logoUrl={logoUrl}
                name={schoolName}
                size="sm"
                className="h-6 w-6 border-none bg-transparent shadow-none"
              />
            </div>
            <div>
              <h4 className="text-xs font-bold leading-tight line-clamp-1">{schoolName}</h4>
              <p className="text-[10px] text-emerald-200 font-mono">EIIN: {eiin || "134567"}</p>
            </div>
          </div>
          <span className="text-[9px] font-bold uppercase tracking-wider bg-emerald-900/80 px-2 py-0.5 rounded text-emerald-100 border border-emerald-700/60">
            Student ID
          </span>
        </div>

        {/* Card Body */}
        <div className="flex-1 px-4 py-3 flex gap-4 items-center">
          {/* Student Photo */}
          <div className="h-24 w-20 shrink-0 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 overflow-hidden flex items-center justify-center shadow-2xs">
            {student.photo ? (
              <img
                src={student.photo}
                alt={student.name_en}
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="text-xl font-bold text-slate-400 font-mono">
                {student.name_en.slice(0, 2).toUpperCase()}
              </span>
            )}
          </div>

          {/* Student Details Grid */}
          <div className="flex-1 min-w-0 space-y-1">
            <h3 className="text-sm font-extrabold text-slate-900 dark:text-slate-100 truncate">
              {currentLang === "bn" && student.name_bn ? student.name_bn : student.name_en}
            </h3>
            <p className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400 font-bold">
              ID: {student.student_id}
            </p>

            <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 pt-1 text-[11px]">
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("academics.class", "Class")}
                </span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {activeEnrollment?.class_name || "—"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("academics.section", "Section")} / {t("students.roll", "Roll")}
                </span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {activeEnrollment?.section_name || "—"} ({activeEnrollment?.roll_no ?? "—"})
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("students.bloodGroup", "Blood")}
                </span>
                <span className="font-semibold text-rose-600 dark:text-rose-400">
                  {student.blood_group || "—"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("institutions.session", "Session")}
                </span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {activeEnrollment?.session_name || "—"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Card Footer */}
        <div className="bg-slate-50 dark:bg-slate-950/80 px-4 py-1.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[9px] text-slate-500 font-mono">
          <span>EMERGENCY: {student.emergency_contact_phone || "+8801XXXXXXXXX"}</span>
          <span className="text-[8px] font-sans font-medium text-slate-400">Authorized Signatory</span>
        </div>
      </div>
    </div>
  );
}
