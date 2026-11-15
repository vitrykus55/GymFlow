"use client";

import { useState } from "react";

import {
  CalendarIcon,
  CheckIcon,
  ChevronIcon,
  DumbbellIcon,
  FlameIcon,
  TargetIcon,
} from "@/components/icons";
import { useAuth } from "@/lib/auth";
import { addDays, formatTime, greeting, isSameDay, now, startOfWeek } from "@/lib/date";
import {
  goal,
  membership,
  todaysWorkout,
  trainingStreakWeeks,
  weekSessions,
  weeklyTarget,
} from "@/lib/mock";

const HOURS = Array.from({ length: 12 }, (_, i) => 9 + i); // 09:00 – 20:00
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function sessionDate(weekStart: Date, dayOffset: number, hour: number, minute = 0): Date {
  const d = addDays(weekStart, dayOffset);
  d.setHours(hour, minute, 0, 0);
  return d;
}

export default function OverviewPage() {
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

  const weekLabel = `${days[0].date.toLocaleDateString("en-US", { month: "long", day: "numeric" })} – ${days[6].date.toLocaleDateString("en-US", { day: "numeric", year: "numeric" })}`;
  const renewsOn = addDays(today, membership.renewsInDays).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
  const used = membership.sessionsTotal - membership.sessionsLeft;

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      {/* Left column */}
      <div className="min-w-0 space-y-6">
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
        {/* Membership */}
        <section className="rounded-3xl bg-night p-6 text-white">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Your membership</h2>
            <span className="rounded-full bg-lime px-3 py-1 text-xs font-bold text-ink">Active</span>
          </div>
          <p className="mt-2 text-xl font-bold">{membership.plan}</p>
          <div className="mt-4 flex items-end justify-between gap-4">
            <div>
              <p className="text-5xl font-extrabold tracking-tight">
                {membership.sessionsLeft} / {membership.sessionsTotal}
              </p>
              <p className="mt-1 text-sm text-white/70">sessions remaining</p>
            </div>
            <p className="border-l border-white/20 pl-4 text-sm text-white/80">Renews {renewsOn}</p>
          </div>
          <div className="mt-5 h-2.5 rounded-full bg-white/15">
            <div
              className="h-full rounded-full bg-lime"
              style={{ width: `${(membership.sessionsLeft / membership.sessionsTotal) * 100}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-white/50">{used} used this month</p>
          <button
            type="button"
            className="mt-5 w-full rounded-full bg-white py-3 text-sm font-bold text-ink hover:bg-lime"
          >
            Manage membership
          </button>
        </section>

        {/* Profile */}
        <section className="rounded-3xl border border-line bg-surface p-6">
          <div className="flex items-center gap-4">
            <span className="grid size-16 place-items-center rounded-full bg-ink text-xl font-bold text-lime">
              {user?.first_name[0]}
              {user?.last_name[0]}
            </span>
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
          <button
            type="button"
            className="mt-3 w-full rounded-full bg-canvas py-3 text-sm font-bold hover:bg-line"
          >
            Edit profile
          </button>
        </section>
      </aside>
    </div>
  );
}

function Stat({
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
