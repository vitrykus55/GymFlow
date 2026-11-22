"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth";
import { demoMembership } from "@/lib/mock";
import type { CurrentMembership, MembershipStatus } from "@/lib/types";

type MembershipState = {
  data: CurrentMembership | null;
  error: string | null;
  loading: boolean;
};

/** The signed-in user's latest membership and Coach entitlement (GET /users/me/membership). */
export function useMembership(): MembershipState {
  const { authFetch, isDemo, user } = useAuth();
  const [state, setState] = useState<MembershipState>({ data: null, error: null, loading: true });
  // Built once so the demo dates don't shift between renders.
  const [demo] = useState(() => ({
    client: demoMembership("client"),
    coach: demoMembership("coach"),
  }));

  useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    authFetch<CurrentMembership>("/api/v1/users/me/membership")
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const error = err instanceof Error ? err.message : "Could not load membership.";
        setState({ data: null, error, loading: false });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, isDemo]);

  if (isDemo) {
    return { data: demo[user?.role ?? "client"] ?? demo.client, error: null, loading: false };
  }
  return state;
}

/**
 * Status as the user should see it: a membership stored as `active` whose interval has
 * already ended is shown as expired (the backend checks timestamps the same way).
 */
export function effectiveStatus(status: MembershipStatus, expiresAt: string, at: Date): MembershipStatus {
  if (status === "active" && new Date(expiresAt) <= at) return "expired";
  return status;
}

export const STATUS_LABEL: Record<MembershipStatus, string> = {
  active: "Active",
  pending: "Pending",
  expired: "Expired",
  cancelled: "Cancelled",
};
