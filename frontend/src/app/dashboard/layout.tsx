"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import {
  BellIcon,
  CalendarIcon,
  CardIcon,
  ChartIcon,
  DumbbellIcon,
  HelpIcon,
  HomeIcon,
  LogoutIcon,
  MessageIcon,
  SearchIcon,
  SettingsIcon,
  UserIcon,
} from "@/components/icons";
import { Logo } from "@/components/logo";
import { useAuth } from "@/lib/auth";
import { now } from "@/lib/date";

const ROLE_LABEL = { client: "Member", trainer: "Coach", admin: "Admin" } as const;

const NAV = [
  { label: "Overview", icon: HomeIcon, active: true },
  { label: "My calendar", icon: CalendarIcon },
  { label: "Workout plan", icon: DumbbellIcon },
  { label: "Progress", icon: ChartIcon },
  { label: "Messages", icon: MessageIcon },
  { label: "Membership", icon: CardIcon },
  { label: "My profile", icon: UserIcon },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { status, user, isDemo, logout } = useAuth();

  useEffect(() => {
    if (status === "guest") router.replace("/login");
  }, [status, router]);

  if (status !== "authenticated" || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="size-8 animate-spin rounded-full border-4 border-line border-t-ink" />
      </div>
    );
  }

  const initials = `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase();

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line bg-surface/60 px-5 py-7 lg:flex">
        <Logo className="px-2" />
        <span className="mt-6 ml-2 w-fit rounded-full bg-canvas px-3 py-1 text-xs font-bold tracking-wide uppercase">
          {ROLE_LABEL[user.role]}
        </span>

        <nav className="mt-6 space-y-1">
          {NAV.map(({ label, icon: Icon, active }) => (
            <button
              key={label}
              type="button"
              disabled={!active}
              title={active ? undefined : "Coming soon"}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] transition ${
                active ? "bg-lime font-bold" : "text-ink/80 hover:bg-canvas disabled:cursor-default"
              }`}
            >
              <Icon />
              {label}
            </button>
          ))}
        </nav>

        <div className="mt-auto space-y-1 border-t border-line pt-5">
          <button
            type="button"
            disabled
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] text-ink/80"
          >
            <SettingsIcon /> Settings
          </button>
          <button
            type="button"
            disabled
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] text-ink/80"
          >
            <HelpIcon /> Help
          </button>
          <button
            type="button"
            onClick={() => void logout()}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] text-ink/80 hover:bg-canvas"
          >
            <LogoutIcon /> Log out
          </button>
          <p className="px-3 pt-4 text-xs text-muted">© {now().getFullYear()} GymFlow</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex items-center gap-4 px-4 py-4 sm:px-8">
          <Logo className="text-xl lg:hidden" />
          <label className="hidden flex-1 items-center gap-3 rounded-full bg-surface px-5 py-2.5 text-muted md:flex">
            <SearchIcon />
            <input
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted"
              placeholder="Search workouts, programs, or help…"
            />
          </label>
          <div className="ml-auto flex items-center gap-4">
            <button type="button" className="relative text-ink/80" aria-label="Notifications">
              <BellIcon width={22} height={22} />
              <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-lime-strong" />
            </button>
            <div className="flex items-center gap-3 border-l border-line pl-4">
              <span className="grid size-10 place-items-center rounded-full bg-ink text-sm font-bold text-lime">
                {initials}
              </span>
              <span className="hidden text-sm font-semibold sm:block">
                {user.first_name} {user.last_name}
              </span>
            </div>
            <button
              type="button"
              onClick={() => void logout()}
              className="text-ink/70 lg:hidden"
              aria-label="Log out"
            >
              <LogoutIcon />
            </button>
          </div>
        </header>

        {isDemo && (
          <p className="mx-4 rounded-xl bg-lime/40 px-4 py-2 text-sm sm:mx-8">
            Demo mode — sample data, nothing is saved.
          </p>
        )}

        <main className="flex-1 px-4 pt-4 pb-10 sm:px-8">{children}</main>
      </div>
    </div>
  );
}
