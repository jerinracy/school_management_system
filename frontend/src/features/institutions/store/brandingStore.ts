import { create } from "zustand";
import { institutionApi, type InstitutionPublicBranding } from "../api/institutionApi";

const BRANDING_STORAGE_KEY = "sms_public_branding_cache";

export const DEMO_INSTITUTION = {
  name_en: "Dhaka Model Academy",
  name_bn: "ঢাকা মডেল একাডেমি",
  eiin: "106601",
  board: "Dhaka",
} as const;

interface BrandingState {
  branding: InstitutionPublicBranding | null;
  isLoading: boolean;
  error: string | null;
  fetchBranding: (force?: boolean) => Promise<InstitutionPublicBranding | null>;
  setBranding: (branding: InstitutionPublicBranding) => void;
  getLocalizedName: (lang: string) => string;
  getLogoUrl: () => string | null;
  getEIIN: () => string;
  getBoard: () => string;
  getLoginBackgroundUrl: () => string | null;
}

function getStoredBranding(): InstitutionPublicBranding | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(BRANDING_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as InstitutionPublicBranding) : null;
  } catch {
    return null;
  }
}

function persistBranding(data: InstitutionPublicBranding | null): void {
  if (typeof window === "undefined") return;
  try {
    if (data) {
      window.localStorage.setItem(BRANDING_STORAGE_KEY, JSON.stringify(data));
    } else {
      window.localStorage.removeItem(BRANDING_STORAGE_KEY);
    }
  } catch {
    // quota exceeded or storage disabled
  }
}

export const useBrandingStore = create<BrandingState>((set, get) => ({
  branding: getStoredBranding(),
  isLoading: false,
  error: null,

  fetchBranding: async (force = false) => {
    const current = get().branding;
    if (current && !force) {
      // Background revalidation
      void institutionApi
        .getPublicBranding()
        .then((fresh) => {
          if (fresh) {
            persistBranding(fresh);
            set({ branding: fresh, error: null });
          }
        })
        .catch(() => {
          // Keep current cached
        });
      return current;
    }

    set({ isLoading: true, error: null });
    try {
      const data = await institutionApi.getPublicBranding();
      persistBranding(data);
      set({ branding: data, isLoading: false, error: null });
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load branding";
      set({ isLoading: false, error: msg });
      return get().branding;
    }
  },

  setBranding: (branding: InstitutionPublicBranding) => {
    persistBranding(branding);
    set({ branding, error: null });
  },

  getLocalizedName: (lang: string) => {
    const b = get().branding;
    if (!b) {
      return lang === "bn" ? DEMO_INSTITUTION.name_bn : DEMO_INSTITUTION.name_en;
    }
    if (lang === "bn") {
      return b.name_bn || b.name_en || DEMO_INSTITUTION.name_bn;
    }
    return b.name_en || b.name_bn || DEMO_INSTITUTION.name_en;
  },

  getLogoUrl: () => {
    const b = get().branding;
    if (!b) return null;
    return b.logo_url || b.logo || null;
  },

  getEIIN: () => {
    const b = get().branding;
    return b?.eiin || DEMO_INSTITUTION.eiin;
  },

  getBoard: () => {
    const b = get().branding;
    return b?.board || DEMO_INSTITUTION.board;
  },

  getLoginBackgroundUrl: () => {
    const b = get().branding;
    if (!b) return null;
    return b.login_background_url || b.login_background || null;
  },
}));
