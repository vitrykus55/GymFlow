"use client";

import { useState, type ReactNode } from "react";

import {
  CalendarIcon,
  CardIcon,
  ChartIcon,
  CheckIcon,
  ChevronIcon,
  PlusIcon,
  UsersIcon,
} from "@/components/icons";
import { MembershipCard } from "@/components/membership-card";
import { Avatar, primaryButton } from "@/components/ui";
import { formatTime, now } from "@/lib/date";
import { coachClients, coachSchedule, coachStats } from "@/lib/mock";
import type { CurrentMembership } from "@/lib/types";

type Props = {
  membership: { data: CurrentMembership | null; loading: boolean; error: string | null };
};

/** Coach home (design: "Your coaching, in flow."). Schedule and clients are sample data for now. */
export function CoachOverview({ membership }: Props) {
  const [today] = useState(now);
  const hour = today.getHours() + today.getMinutes() / 60;
  const nextIndex = coachSchedule.findIndex((s) => s.hour + s.minutes / 60 > hour);
  const dateLabel = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      <div className="min-w-0 space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
              Your coaching, in flow.
            </h1>
            <p className="mt-2 text-lg text-muted">A clear view of your clients and your day.</p>
          </div>
          <button type="button" disabled title="Coming soon" className={primaryButton}>
            <PlusIcon width={18} height={18} /> Create workout
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-y-4 rounded-2xl bg-surface/70 p-4 ring-1 ring-line lg:grid-cols-4 lg:divide-x lg:divide-line">
          <CoachStat icon={<UsersIcon />} value={coachStats.activeClients} label="Active clients" />
          <CoachStat icon={<CalendarIcon />} value={coachSchedule.length} label="Sessions today" />
          <CoachStat icon={<CardIcon />} value={coachStats.renewals} label="Membership renewals" />
          <CoachStat icon={<ChartIcon />} value={`${coachStats.attendance}%`} label="Attendance" />
        </div>

        {/* Schedule */}
        <section className="rounded-3xl border border-line bg-surface p-5 sm:p-6">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h2 className="text-2xl font-extrabold tracking-tight">Your schedule</h2>
            <span className="text-sm text-muted">{dateLabel}</span>
          </div>
          <ul className="mt-4 divide-y divide-line">
            {coachSchedule.map((s, i) => {
              const done = s.hour + s.minutes / 60 <= hour;
              const isNext = i === nextIndex;
              return (
                <li key={s.hour} className="flex items-center gap-4 py-2.5">
                  <span className="w-14 shrink-0 text-lg font-bold tabular-nums">
                    {formatTime(s.hour)}
                  </span>
                  <div
                    className={`flex min-w-0 flex-1 items-center gap-3 rounded-xl px-4 py-3 ${
                      isNext ? "bg-lime/60" : "bg-canvas"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-bold">
                        {s.title} <span className="font-normal text-ink/70">· {s.client}</span>
                      </p>
                      <p className="text-xs text-muted">{s.minutes} min</p>
                    </div>
                    {done && (
                      <span className="grid size-6 place-items-center rounded-full bg-lime">
                        <CheckIcon width={14} height={14} strokeWidth={3} />
                      </span>
                    )}
                    <ChevronIcon width={18} height={18} className="text-muted" />
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        {/* Clients */}
        <section className="rounded-3xl border border-line bg-surface p-5 sm:p-6">
          <h2 className="text-2xl font-extrabold tracking-tight">Your clients</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-3 font-medium">Client</th>
                  <th className="pb-3 font-medium">Plan</th>
                  <th className="pb-3 font-medium">Sessions left</th>
                  <th className="pb-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {coachClients.map((c) => {
                  const [first, last = ""] = c.name.split(" ");
                  return (
                    <tr key={c.name}>
                      <td className="py-3">
                        <span className="flex items-center gap-3 font-bold">
                          <Avatar firstName={first} lastName={last} size="sm" />
                          {c.name}
                        </span>
                      </td>
                      <td className="py-3">{c.plan}</td>
                      <td className="py-3 tabular-nums">
                        {c.sessionsLeft} / {c.sessionsTotal}
                      </td>
                      <td className="py-3">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-bold ${
                            c.renewSoon ? "bg-amber-100 text-amber-900" : "bg-lime/50"
                          }`}
                        >
                          {c.renewSoon ? "Renew soon" : "Active"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <aside className="space-y-6">
        <MembershipCard {...membership} title="Coach membership" />

        <section className="rounded-3xl border border-line bg-surface p-6">
          <h2 className="flex items-center gap-2 text-xl font-extrabold">
            <CardIcon /> Renewal reminders
          </h2>
          <p className="mt-2 text-sm text-muted">
            {coachStats.renewals} client memberships end this week.
          </p>
          <ul className="mt-4 space-y-2 text-sm">
            {coachClients
              .filter((c) => c.renewSoon)
              .map((c) => (
                <li key={c.name} className="flex justify-between rounded-xl bg-canvas px-4 py-2.5">
                  <span className="font-semibold">{c.name}</span>
                  <span className="text-muted">{c.sessionsLeft} sessions left</span>
                </li>
              ))}
          </ul>
        </section>
      </aside>
    </div>
  );
}

function CoachStat({ icon, value, label }: { icon: ReactNode; value: ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-3 px-2 lg:px-5 lg:first:pl-2">
      <span className="text-ink/70">{icon}</span>
      <div>
        <p className="text-3xl font-extrabold tabular-nums">{value}</p>
        <p className="text-sm text-muted">{label}</p>
      </div>
    </div>
  );
}
