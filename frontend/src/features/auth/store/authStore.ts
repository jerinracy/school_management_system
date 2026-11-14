import { create } from "zustand";

export interface AuthUser {
  id: string;
  username: string;
  full_name: string;
  phone: string;
  email: string;
  user_type: string;
  institution_id: string | null;
  roles: string[];
  permissions?: string[];
  must_change_password?: boolean;
  language_preference?: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isRestoring: boolean;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: AuthUser | null) => void;
  updateUserPreferences: (prefs: Partial<AuthUser>) => void;
  logout: () => void;
  setIsRestoring: (loading: boolean) => void;
}

const REFRESH_STORAGE_KEY = "sms_auth_refresh_token";

function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    return null;
  }
}

function persistRefreshToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) {
      window.sessionStorage.setItem(REFRESH_STORAGE_KEY, token);
    } else {
      window.sessionStorage.removeItem(REFRESH_STORAGE_KEY);
    }
  } catch {
    // sessionStorage unavailable or quota exceeded
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: getStoredRefreshToken(),
  user: null,
  isAuthenticated: false,
  isRestoring: true,

  setTokens: (access: string, refresh: string) => {
    persistRefreshToken(refresh);
    set({
      accessToken: access,
      refreshToken: refresh,
      isAuthenticated: true,
    });
  },

  setUser: (user: AuthUser | null) => {
    set({
      user,
      isAuthenticated: Boolean(user),
    });
  },

  updateUserPreferences: (prefs: Partial<AuthUser>) => {
    set((state) => ({
      user: state.user ? { ...state.user, ...prefs } : null,
    }));
  },

  logout: () => {
    persistRefreshToken(null);
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      isRestoring: false,
    });
  },

  setIsRestoring: (isRestoring: boolean) => {
    set({ isRestoring });
  },
}));
