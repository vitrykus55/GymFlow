"use client";

import { useState } from "react";

import { Skeleton } from "@/components/ui";
import { daysUntil, formatDate, now } from "@/lib/date";
import { effectiveStatus, STATUS_LABEL } from "@/lib/membership";
import type { CurrentMembership, MembershipStatus } from "@/lib/types";

const BADGE: Record<MembershipStatus, string> = {
  active: "bg-lime text-ink",
  pending: "bg-amber-200 text-amber-950",
  expired: "bg-white/15 text-white/80",
  cancelled: "bg-white/15 text-white/80",
};

type Props = {
  data: CurrentMembership | null;
  loading: boolean;
  error: string | null;
};

/** Dark membership card (design: "Your membership") driven by GET /users/me/membership. */
export function MembershipCard({ data, loading, error }: Props) {
  const [today] = useState(now);
  const membership = data?.membership ?? null;

  return (
    <section className="rounded-3xl bg-night p-6 text-white">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold">Your membership</h2>
        {membership && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${
              BADGE[effectiveStatus(membership.status, membership.expires_at, today)]
            }`}
          >
            {STATUS_LABEL[effectiveStatus(membership.status, membership.expires_at, today)]}
          </span>
        )}
      </div>

      {loading ? (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-6 w-32 bg-white/10" />
          <Skeleton className="h-12 w-40 bg-white/10" />
          <Skeleton className="h-2.5 w-full bg-white/10" />
        </div>
      ) : error ? (
        <p className="mt-4 text-sm text-white/70">{error}</p>
      ) : membership ? (
        <ActiveMembership
          name={membership.membership_type.name}
          startsAt={membership.starts_at}
          expiresAt={membership.expires_at}
          status={effectiveStatus(membership.status, membership.expires_at, today)}
          today={today}
        />
      ) : (
        <div className="mt-3">
          <p className="text-2xl font-extrabold tracking-tight">No membership yet</p>
          <p className="mt-1 text-sm text-white/60">
            Plans and online payments are coming soon. Ask the front desk to get started.
          </p>
        </div>
      )}

      <button
        type="button"
        disabled
        title="Coming soon"
        className="mt-5 w-full rounded-full bg-white/10 py-3 text-sm font-bold text-white/70 ring-1 ring-white/15 disabled:cursor-not-allowed"
      >
        {membership ? "Manage membership" : "Browse plans"} · soon
      </button>
    </section>
  );
}

function ActiveMembership({
  name,
  startsAt,
  expiresAt,
  status,
  today,
}: {
  name: string;
  startsAt: string;
  expiresAt: string;
  status: MembershipStatus;
  today: Date;
}) {
  const start = new Date(startsAt);
  const end = new Date(expiresAt);
  const total = Math.max(1, daysUntil(end, start));
  const left = Math.max(0, daysUntil(end, today));
  const isLive = status === "active";

  return (
    <>
      <p className="mt-2 text-xl font-bold">{name}</p>
      <div className="mt-4 flex items-end justify-between gap-4">
        <div>
          <p className="text-5xl font-extrabold tracking-tight">{isLive ? left : "—"}</p>
          <p className="mt-1 text-sm text-white/70">
            {isLive ? (left === 1 ? "day remaining" : "days remaining") : `${STATUS_LABEL[status].toLowerCase()} membership`}
          </p>
        </div>
        <p className="border-l border-white/20 pl-4 text-sm text-white/80">
          {status === "pending" ? "Starts" : isLive ? "Renews" : "Ended"}{" "}
          {formatDate(status === "pending" ? startsAt : expiresAt)}
        </p>
      </div>
      <div className="mt-5 h-2.5 rounded-full bg-white/15">
        <div
          className="h-full rounded-full bg-lime transition-[width]"
          style={{ width: `${isLive ? Math.min(100, (left / total) * 100) : 0}%` }}
        />
      </div>
    </>
  );
}
