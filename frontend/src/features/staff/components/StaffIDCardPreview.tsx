import { useTranslation } from "react-i18next";
import { Download, Printer, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AcademicLogo } from "@/features/institutions/components/AcademicLogo";
import { useBrandingStore } from "@/features/institutions/store/brandingStore";
import type { StaffDetail } from "@/features/staff/api/staffApi";

interface StaffIDCardPreviewProps {
  staff: StaffDetail;
  onDownloadPdf?: () => void;
}

export function StaffIDCardPreview({
  staff,
  onDownloadPdf,
}: StaffIDCardPreviewProps) {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const { getLocalizedName, getLogoUrl, getEIIN } = useBrandingStore();

  const schoolName = getLocalizedName(currentLang);
  const logoUrl = getLogoUrl();
  const eiin = getEIIN();

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Top Action Bar */}
      <div className="flex items-center gap-3 w-full justify-between max-w-[480px]">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span>{t("staff.officialCard", "Institutional Staff Identity Card")}</span>
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

      {/* Printable CR80 Standard Card: 3.370 × 2.125 inches (Approx 480 × 300 px) */}
      <div
        id="staff-id-card-print"
        className="w-[460px] h-[280px] rounded-2xl border-2 border-emerald-800/40 bg-white dark:bg-slate-900 shadow-xl overflow-hidden flex flex-col justify-between relative print:m-0 print:border-emerald-800"
      >
        {/* Top Header Banner */}
        <div className="bg-emerald-800 text-white px-4 py-2.5 flex items-center justify-between border-b-2 border-emerald-900 shadow-xs">
          <div className="flex items-center gap-2.5">
            <AcademicLogo
              logoUrl={logoUrl}
              name={schoolName}
              size="sm"
              className="h-9 w-9 rounded-md bg-white p-0.5"
            />
            <div>
              <h4 className="text-xs font-bold leading-tight line-clamp-1">
                {schoolName}
              </h4>
              <p className="text-[10px] text-emerald-200 font-mono">
                {t("auth.eiinLabel", "EIIN")}: {eiin}
              </p>
            </div>
          </div>
          <span className="text-[9px] font-bold uppercase tracking-wider bg-emerald-900/80 px-2 py-0.5 rounded text-emerald-100 border border-emerald-700/60">
            {t("staff.staffIdBadge", "Staff ID")}
          </span>
        </div>

        {/* Card Body */}
        <div className="flex-1 px-4 py-3 flex gap-4 items-center">
          {/* Photo Box */}
          <div className="h-24 w-20 shrink-0 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 overflow-hidden flex items-center justify-center shadow-2xs">
            {staff.photo ? (
              <img
                src={staff.photo}
                alt={staff.full_name_en}
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="text-xl font-bold text-slate-400 font-mono">
                {staff.full_name_en.slice(0, 2).toUpperCase()}
              </span>
            )}
          </div>

          {/* Details */}
          <div className="flex-1 min-w-0 space-y-1">
            <h3 className="text-sm font-extrabold text-slate-900 dark:text-slate-100 truncate">
              {currentLang === "bn" && staff.full_name_bn
                ? staff.full_name_bn
                : staff.full_name_en}
            </h3>
            <p className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400 font-bold">
              ID: {staff.employee_id}
            </p>

            <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 pt-1 text-[11px]">
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("staff.designation", "Designation")}
                </span>
                <span className="font-semibold text-slate-800 dark:text-slate-200 truncate block">
                  {staff.designation_title || "—"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("staff.department", "Department")}
                </span>
                <span className="font-semibold text-slate-800 dark:text-slate-200 truncate block">
                  {staff.department_name || "—"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("students.bloodGroup", "Blood Group")}
                </span>
                <span className="font-semibold text-rose-600 dark:text-rose-400">
                  {staff.blood_group || "—"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  {t("staff.mpoIndex", "MPO Index")}
                </span>
                <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">
                  {staff.mpo_index_number || (staff.is_mpo ? t("common.yes", "Yes") : "—")}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Card Footer */}
        <div className="bg-slate-50 dark:bg-slate-950/80 px-4 py-1.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[9px] text-slate-500 font-mono">
          <span>{t("staff.phone", "PHONE")}: {staff.phone}</span>
          <span className="text-[8px] font-sans font-medium text-slate-400">
            {t("staff.authorizedSignatory", "Authorized Signatory")}
          </span>
        </div>
      </div>
    </div>
  );
}
