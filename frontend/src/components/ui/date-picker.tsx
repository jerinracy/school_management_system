import * as PopoverPrimitive from "@radix-ui/react-popover";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toLocaleDigits } from "@/lib/format";
import { cn } from "@/lib/utils";

const MONTHS_EN = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const MONTHS_BN = [
  "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
  "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
];

const WEEKDAYS_EN = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const WEEKDAYS_BN = ["রবি", "সোম", "মঙ্গল", "বুধ", "বৃহ", "শুক্র", "শনি"];

interface DatePickerProps {
  value?: Date;
  onChange: (date: Date) => void;
  placeholder?: string;
  className?: string;
  "aria-label"?: string;
}

export function DatePicker({
  value,
  onChange,
  placeholder,
  className,
  "aria-label": ariaLabel,
}: DatePickerProps) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const initial = value ?? new Date();
  const [viewYear, setViewYear] = useState(initial.getFullYear());
  const [viewMonth, setViewMonth] = useState(initial.getMonth());

  const isBn = i18n.language === "bn";
  const months = isBn ? MONTHS_BN : MONTHS_EN;
  const weekdays = isBn ? WEEKDAYS_BN : WEEKDAYS_EN;

  const days = useMemo(() => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const totalDays = new Date(viewYear, viewMonth + 1, 0).getDate();
    const cells: Array<number | null> = Array.from({ length: firstDay }, () => null);
    for (let d = 1; d <= totalDays; d += 1) {
      cells.push(d);
    }
    return cells;
  }, [viewYear, viewMonth]);

  const formattedValue = useMemo(() => {
    if (!value) return null;
    const day = toLocaleDigits(String(value.getDate()).padStart(2, "0"), i18n.language);
    const monthName = months[value.getMonth()] ?? "";
    const year = toLocaleDigits(value.getFullYear(), i18n.language);
    return `${day} ${monthName} ${year}`;
  }, [value, i18n.language, months]);

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  };

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          type="button"
          aria-label={ariaLabel ?? t("ui.datePicker.selectDate")}
          className={cn(
            "flex h-8 w-full items-center justify-between gap-2 rounded-md border border-border bg-surface px-2.5 text-xs text-ink shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
            className,
          )}
        >
          <span className={cn("tabular-nums truncate", !formattedValue && "text-ink-subtle")}>
            {formattedValue ?? (placeholder ?? t("ui.datePicker.placeholder"))}
          </span>
          <CalendarIcon className="h-3.5 w-3.5 shrink-0 text-ink-subtle" />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          sideOffset={4}
          className="z-50 w-64 rounded-md border border-border bg-surface p-3 shadow-lg"
        >
          <div className="mb-2 flex items-center justify-between">
            <button
              type="button"
              onClick={prevMonth}
              aria-label={t("ui.datePicker.prevMonth")}
              className="rounded p-1 text-ink-muted hover:bg-canvas hover:text-ink"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="tabular-nums text-xs font-semibold text-ink">
              {months[viewMonth]} {toLocaleDigits(viewYear, i18n.language)}
            </span>
            <button
              type="button"
              onClick={nextMonth}
              aria-label={t("ui.datePicker.nextMonth")}
              className="rounded p-1 text-ink-muted hover:bg-canvas hover:text-ink"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center">
            {weekdays.map((wd) => (
              <span key={wd} className="py-1 text-[10px] font-medium text-ink-subtle">
                {wd}
              </span>
            ))}
            {days.map((day, idx) => {
              if (!day) return <span key={`empty-${idx}`} />;
              const isSelected =
                value &&
                value.getFullYear() === viewYear &&
                value.getMonth() === viewMonth &&
                value.getDate() === day;
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => {
                    onChange(new Date(viewYear, viewMonth, day));
                    setOpen(false);
                  }}
                  className={cn(
                    "tabular-nums flex h-7 w-7 items-center justify-center rounded text-xs transition-colors",
                    isSelected
                      ? "bg-primary font-semibold text-white"
                      : "text-ink hover:bg-canvas",
                  )}
                >
                  {toLocaleDigits(day, i18n.language)}
                </button>
              );
            })}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
