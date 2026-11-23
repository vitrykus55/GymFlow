"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import {
  CalendarIcon,
  CheckIcon,
  ChevronIcon,
  DumbbellIcon,
  FlameIcon,
  TargetIcon,
} from "@/components/icons";
import { MembershipCard } from "@/components/membership-card";
import { Avatar, secondaryButton } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { addDays, formatTime, greeting, isSameDay, now, startOfWeek } from "@/lib/date";
import {
  goal,
  todaysWorkout,
  trainingStreakWeeks,
  weekSessions,
  weeklyTarget,
} from "@/lib/mock";
import type { CurrentMembership } from "@/lib/types";

const HOURS = Array.from({ length: 12 }, (_, i) => 9 + i); // 09:00 – 20:00
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function sessionDate(weekStart: Date, dayOffset: number, hour: number, minute = 0): Date {
  const d = addDays(weekStart, dayOffset);
  d.setHours(hour, minute, 0, 0);
  return d;
}

type Props = {
  membership: { data: CurrentMembership | null; loading: boolean; error: string | null };
  notice?: ReactNode;
};

export function MemberOverview({ membership, notice }: Props) {
  const { user } = useAuth();
  const [today] = useState(now);
  const [weekShift, setWeekShift] = useState(0);

  const currentWeekStart = startOfWeek(today);
  const weekStart = addDays(currentWeekStart, weekShift * 7);
  const days = DAY_NAMES.map((name, i) => ({ name, date: addDays(weekStart, i) }));
  const sessions = weekSessions.map((s) => ({
    ...s,
    date: sessionDate(weekStart, s.dayOffset, s.hour, s.minute),
  }));

  const thisWeek = weekSessions.map((s) => sessionDate(currentWeekStart, s.dayOffset, s.hour, s.minute));
  const doneThisWeek = thisWeek.filter((d) => d < today).length;
  const next = thisWeek.find((d) => d >= today) ?? sessionDate(addDays(currentWeekStart, 7), 0, 18);
  const nextLabel = isSameDay(next, today)
    ? `Today, ${formatTime(next.getHours(), next.getMinutes())}`
    : `${next.toLocaleDateString("en-US", { weekday: "short" })}, ${formatTime(next.getHours(), next.getMinutes())}`;

  const weekStartLabel = days[0].date.toLocaleDateString("en-US", { month: "long", day: "numeric" });
  const weekEnd = days[6].date;
  const weekEndLabel =
    weekEnd.getMonth() === days[0].date.getMonth()
      ? String(weekEnd.getDate())
      : weekEnd.toLocaleDateString("en-US", { month: "long", day: "numeric" });
  const weekLabel = `${weekStartLabel} – ${weekEndLabel}, ${weekEnd.getFullYear()}`;

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      {/* Left column */}
      <div className="min-w-0 space-y-6">
        {notice}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
              {greeting(today)}, {user?.first_name}.
            </h1>
            <p className="mt-2 text-lg text-muted">Your next step starts here.</p>
          </div>
          <button
            type="button"
            className="rounded-full bg-ink px-6 py-3 text-sm font-bold text-white hover:bg-black"
          >
            Book a session
          </button>
        </div>

        {/* Stats */}
        <div className="grid divide-line rounded-2xl sm:grid-cols-3 sm:divide-x">
          <Stat icon={<DumbbellIcon width={26} height={26} />} label="This week">
            {doneThisWeek} of {weeklyTarget} workouts
          </Stat>
          <Stat icon={<FlameIcon width={26} height={26} />} label="Training streak">
            {trainingStreakWeeks} weeks
          </Stat>
          <Stat icon={<CalendarIcon width={26} height={26} />} label="Next session">
            {nextLabel}
          </Stat>
        </div>

        {/* Calendar */}
        <section className="rounded-3xl border border-line bg-surface p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-extrabold tracking-tight">Your training calendar</h2>
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Previous week"
                onClick={() => setWeekShift((w) => w - 1)}
                className="grid size-8 place-items-center rounded-full hover:bg-canvas"
              >
                <ChevronIcon className="rotate-180" width={18} height={18} />
              </button>
              <span className="min-w-44 text-center text-sm font-semibold">{weekLabel}</span>
              <button
                type="button"
                aria-label="Next week"
                onClick={() => setWeekShift((w) => w + 1)}
                className="grid size-8 place-items-center rounded-full hover:bg-canvas"
              >
                <ChevronIcon width={18} height={18} />
              </button>
            </div>
          </div>

          <div className="mt-5 overflow-x-auto">
            <div className="grid min-w-[640px] grid-cols-[52px_repeat(7,1fr)]">
              <div />
              {days.map(({ name, date }) => (
                <div key={name} className="pb-3 text-center text-sm">
                  <span
                    className={`inline-block rounded-lg px-3 py-1 ${
                      isSameDay(date, today) ? "bg-lime font-bold" : ""
                    }`}
                  >
                    {name} {date.getDate()}
                  </span>
                </div>
              ))}

              {HOURS.map((hour) => (
                <div key={hour} className="contents">
                  <div className="h-11 -translate-y-2 pr-2 text-right text-xs text-muted">
                    {formatTime(hour)}
                  </div>
                  {days.map(({ date }, i) => {
                    const s = sessions.find(
                      (x) => x.dayOffset === i && x.hour === hour && isSameDay(x.date, date),
                    );
                    const done = s ? s.date < today : false;
                    const isToday = s ? isSameDay(s.date, today) : false;
                    return (
                      <div key={i} className="relative h-11 border-t border-l border-line">
                        {s && (
                          <div
                            className={`absolute inset-x-1 top-1 z-10 rounded-lg px-2 py-1.5 text-xs ${
                              isToday ? "bg-lime" : "bg-canvas"
                            }`}
                          >
                            <p className="flex items-center gap-1 font-bold">
                              {done && <CheckIcon width={12} height={12} strokeWidth={3} />}
                              {s.title}
                            </p>
                            <p className="text-ink/70">{formatTime(s.hour, s.minute)}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 flex gap-5 text-xs text-muted">
            <span className="flex items-center gap-1.5">
              <span className="grid size-3.5 place-items-center rounded bg-lime">
                <CheckIcon width={10} height={10} strokeWidth={3} />
              </span>
              Completed
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-3.5 rounded bg-canvas ring-1 ring-line" />
              Upcoming
            </span>
          </div>
        </section>

        {/* Today's workout */}
        <section className="rounded-3xl border border-line bg-surface p-6">
          <h2 className="text-2xl font-extrabold tracking-tight">Today&apos;s workout</h2>
          <p className="mt-3 text-xl font-bold">{todaysWorkout.title}</p>
          <p className="text-sm text-muted">
            {todaysWorkout.duration} · {todaysWorkout.coach}
          </p>
          <ul className="mt-4 divide-y divide-line">
            {todaysWorkout.exercises.map((ex) => (
              <li key={ex.name} className="flex justify-between py-2.5 text-sm">
                <span>{ex.name}</span>
                <span className="font-semibold">{ex.sets}</span>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="mt-4 rounded-full bg-ink px-6 py-2.5 text-sm font-bold text-white hover:bg-black"
          >
            Open workout
          </button>
        </section>
      </div>

      {/* Right column */}
      <aside className="space-y-6">
        <MembershipCard {...membership} />

        {/* Profile */}
        <section className="rounded-3xl border border-line bg-surface p-6">
          <div className="flex items-center gap-4">
            <Avatar firstName={user?.first_name ?? ""} lastName={user?.last_name ?? ""} />
            <div className="min-w-0">
              <p className="truncate text-xl font-extrabold">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="truncate text-sm text-muted">{user?.email}</p>
            </div>
          </div>
          <dl className="mt-5 divide-y divide-line text-sm">
            <div className="flex items-center justify-between py-3">
              <dt className="flex items-center gap-2 text-muted">
                <TargetIcon width={18} height={18} /> Goal
              </dt>
              <dd className="font-semibold">{goal}</dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="flex items-center gap-2 text-muted">
                <CalendarIcon width={18} height={18} /> Weekly target
              </dt>
              <dd className="font-semibold">{weeklyTarget} sessions</dd>
            </div>
          </dl>
          <Link href="/dashboard/profile" className={`${secondaryButton} mt-3 w-full`}>
            Edit profile
          </Link>
        </section>
      </aside>
    </div>
  );
}

export function Stat({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-4 py-3 sm:px-6 sm:first:pl-0">
      <span className="text-ink/80">{icon}</span>
      <div>
        <p className="text-sm text-muted">{label}</p>
        <p className="text-lg font-bold">{children}</p>
      </div>
    </div>
  );
}
