import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import bn from "./locales/bn.json";
import en from "./locales/en.json";

export const LANGUAGE_STORAGE_KEY = "sms_dashboard_lang";
export type SupportedLanguage = "en" | "bn";

function getInitialLanguage(): SupportedLanguage {
  if (typeof window === "undefined") {
    return "en";
  }
  const saved = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return saved === "bn" ? "bn" : "en";
}

function syncDocumentLanguage(lng: string): void {
  if (typeof document !== "undefined") {
    document.documentElement.lang = lng === "bn" ? "bn" : "en";
  }
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    bn: { translation: bn },
  },
  lng: getInitialLanguage(),
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
  react: {
    useSuspense: false,
  },
});

syncDocumentLanguage(i18n.language);

i18n.on("languageChanged", (lng) => {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lng);
  }
  syncDocumentLanguage(lng);
});

export function setAppLanguage(lng: SupportedLanguage): void {
  void i18n.changeLanguage(lng);
}

export default i18n;
