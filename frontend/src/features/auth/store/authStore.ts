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

const ACCESS_STORAGE_KEY = "sms_auth_access_token";
const REFRESH_STORAGE_KEY = "sms_auth_refresh_token";
const USER_STORAGE_KEY = "sms_auth_user";

function getStoredItem(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(key) ?? window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function setStoredItem(key: string, value: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (value) {
      window.localStorage.setItem(key, value);
    } else {
      window.localStorage.removeItem(key);
      try {
        window.sessionStorage.removeItem(key);
      } catch {
        // ignore
      }
    }
  } catch {
    // In restricted browsing / quota exceeded, fallback to sessionStorage
    try {
      if (value) {
        window.sessionStorage.setItem(key, value);
      } else {
        window.sessionStorage.removeItem(key);
      }
    } catch {
      // Storage completely unavailable
    }
  }
}

function getStoredUser(): AuthUser | null {
  const raw = getStoredItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

const initialRefreshToken = getStoredItem(REFRESH_STORAGE_KEY);
const initialAccessToken = getStoredItem(ACCESS_STORAGE_KEY);
const initialUser = getStoredUser();
const hasInitialAuth = Boolean(initialRefreshToken && initialUser);

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: initialAccessToken,
  refreshToken: initialRefreshToken,
  user: initialUser,
  isAuthenticated: hasInitialAuth,
  isRestoring: false,

  setTokens: (access: string, refresh: string) => {
    setStoredItem(ACCESS_STORAGE_KEY, access);
    setStoredItem(REFRESH_STORAGE_KEY, refresh);
    set({
      accessToken: access,
      refreshToken: refresh,
      isAuthenticated: true,
    });
  },

  setUser: (user: AuthUser | null) => {
    setStoredItem(USER_STORAGE_KEY, user ? JSON.stringify(user) : null);
    set((state) => ({
      user,
      isAuthenticated: Boolean(user && state.refreshToken),
    }));
  },

  updateUserPreferences: (prefs: Partial<AuthUser>) => {
    set((state) => {
      const updated = state.user ? { ...state.user, ...prefs } : null;
      setStoredItem(USER_STORAGE_KEY, updated ? JSON.stringify(updated) : null);
      return { user: updated };
    });
  },

  logout: () => {
    setStoredItem(ACCESS_STORAGE_KEY, null);
    setStoredItem(REFRESH_STORAGE_KEY, null);
    setStoredItem(USER_STORAGE_KEY, null);
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
