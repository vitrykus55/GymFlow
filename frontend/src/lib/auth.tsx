"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiFetch } from "@/lib/api";

export type UserRole = "client" | "trainer" | "admin";

export type CurrentUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
};

export type RegisterData = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
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
  startDemo: () => void;
};

const DEMO_USER: CurrentUser = {
  id: 0,
  email: "emma@gymflow.app",
  first_name: "Emma",
  last_name: "Wilson",
  role: "client",
};

const AuthContext = createContext<AuthContextValue | null>(null);

// The refresh token rotates on every use, so the session must be restored only once
// per page load (React Strict Mode runs effects twice in development).
let restorePromise: Promise<Session | null> | null = null;

function restoreSession(): Promise<Session | null> {
  restorePromise ??= apiFetch<AccessTokenResponse>("/api/v1/auth/refresh", { method: "POST" })
    .then(async ({ access_token }) => ({
      user: await fetchMe(access_token),
      accessToken: access_token,
    }))
    .catch(() => null);
  return restorePromise;
}

function fetchMe(accessToken: string): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [session, setSession] = useState<Session | null>(null);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void restoreSession().then((restored) => {
      if (cancelled) return;
      setSession(restored);
      setStatus(restored ? "authenticated" : "guest");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiFetch<AccessTokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const user = await fetchMe(access_token);
    setSession({ user, accessToken: access_token });
    setIsDemo(false);
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (data: RegisterData) => {
      await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ ...data, phone: data.phone || null }),
      });
      await login(data.email, data.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    if (!isDemo) {
      await apiFetch<void>("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    }
    restorePromise = Promise.resolve(null);
    setSession(null);
    setIsDemo(false);
    setStatus("guest");
  }, [isDemo]);

  const startDemo = useCallback(() => {
    setSession({ user: DEMO_USER, accessToken: null });
    setIsDemo(true);
    setStatus("authenticated");
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
    }),
    [status, session, isDemo, login, register, logout, startDemo],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
