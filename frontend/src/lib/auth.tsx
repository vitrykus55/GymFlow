"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError, apiFetch } from "@/lib/api";
import { DEMO_USERS } from "@/lib/mock";
import type { CurrentUser, UserRole } from "@/lib/types";

export type { CurrentUser, UserRole } from "@/lib/types";

export type RegisterData = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  birth_date?: string | null;
};

type AccessTokenResponse = { access_token: string; token_type: "bearer" };
type Session = { user: CurrentUser; accessToken: string | null };
type Status = "loading" | "authenticated" | "guest";

type AuthContextValue = {
  status: Status;
  user: CurrentUser | null;
  isDemo: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  startDemo: (role?: UserRole) => void;
  /** Calls an authenticated endpoint; refreshes the access token once on 401. */
  authFetch: <T>(path: string, init?: RequestInit) => Promise<T>;
  /** Keeps the header/sidebar in sync after the profile changes. */
  updateUser: (patch: Partial<CurrentUser>) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

// The refresh token rotates on every use, so concurrent refreshes would revoke each other.
// Every caller shares the same in-flight request.
let refreshInFlight: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  refreshInFlight ??= apiFetch<AccessTokenResponse>("/api/v1/auth/refresh", { method: "POST" })
    .then(({ access_token }) => access_token)
    .catch(() => null)
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

// Restore the session only once per page load (React Strict Mode runs effects twice).
let restorePromise: Promise<Session | null> | null = null;

function restoreSession(): Promise<Session | null> {
  restorePromise ??= refreshAccessToken().then(async (token) => {
    if (!token) return null;
    try {
      return { user: await fetchMe(token), accessToken: token };
    } catch {
      return null;
    }
  });
  return restorePromise;
}

function fetchMe(accessToken: string): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

function withToken(init: RequestInit | undefined, token: string | null): RequestInit {
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [session, setSession] = useState<Session | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const tokenRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void restoreSession().then((restored) => {
      if (cancelled) return;
      tokenRef.current = restored?.accessToken ?? null;
      setSession(restored);
      setStatus(restored ? "authenticated" : "guest");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const signOutLocally = useCallback(() => {
    restorePromise = Promise.resolve(null);
    tokenRef.current = null;
    setSession(null);
    setIsDemo(false);
    setStatus("guest");
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiFetch<AccessTokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const user = await fetchMe(access_token);
    tokenRef.current = access_token;
    setSession({ user, accessToken: access_token });
    setIsDemo(false);
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (data: RegisterData) => {
      await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          ...data,
          phone: data.phone || null,
          birth_date: data.birth_date || null,
        }),
      });
      await login(data.email, data.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    if (!isDemo) {
      await apiFetch<void>("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    }
    signOutLocally();
  }, [isDemo, signOutLocally]);

  const startDemo = useCallback((role: UserRole = "client") => {
    tokenRef.current = null;
    setSession({ user: DEMO_USERS[role], accessToken: null });
    setIsDemo(true);
    setStatus("authenticated");
  }, []);

  const authFetch = useCallback(
    async <T,>(path: string, init?: RequestInit): Promise<T> => {
      try {
        return await apiFetch<T>(path, withToken(init, tokenRef.current));
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 401) throw err;
        const fresh = await refreshAccessToken();
        if (!fresh) {
          signOutLocally();
          throw err;
        }
        tokenRef.current = fresh;
        return apiFetch<T>(path, withToken(init, fresh));
      }
    },
    [signOutLocally],
  );

  const updateUser = useCallback((patch: Partial<CurrentUser>) => {
    setSession((s) => (s ? { ...s, user: { ...s.user, ...patch } } : s));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: session?.user ?? null,
      isDemo,
      login,
      register,
      logout,
      startDemo,
      authFetch,
      updateUser,
    }),
    [status, session, isDemo, login, register, logout, startDemo, authFetch, updateUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
