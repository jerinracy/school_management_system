const BANGLA_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];
export const BANGLA_DIGITS_STORAGE_KEY = "sms_use_bangla_digits";

export function getUseBanglaDigits(): boolean {
  if (typeof window === "undefined") return true;
  const stored = window.localStorage.getItem(BANGLA_DIGITS_STORAGE_KEY);
  if (stored === null) return true; // default to true
  return stored === "true";
}

export function setUseBanglaDigits(useDigits: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(BANGLA_DIGITS_STORAGE_KEY, String(useDigits));
}

export function toLocaleDigits(input: string | number, language: string): string {
  const raw = String(input);
  if (language !== "bn" || !getUseBanglaDigits()) {
    return raw;
  }
  return raw.replace(/\d/g, (digit) => BANGLA_DIGITS[Number(digit)] ?? digit);
}

export function formatTimeShort(date: Date, language: string): string {
  const locale = language === "bn" ? "bn-BD" : "en-US";
  const formatted = new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
  return toLocaleDigits(formatted, language);
}

export function formatDate(date: Date | string, language: string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const locale = language === "bn" ? "bn-BD" : "en-US";
  const formatted = new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);
  return toLocaleDigits(formatted, language);
}

export function formatCurrencyBDT(amount: number | string, language: string): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  const valid = isNaN(num) ? 0 : num;
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(valid);

  const prefix = language === "bn" ? "৳ " : "BDT ";
  return `${prefix}${toLocaleDigits(formatted, language)}`;
}
