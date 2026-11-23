"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ComponentType, type SVGProps } from "react";

import {
  BellIcon,
  CalendarIcon,
  CardIcon,
  ChartIcon,
  ClipboardIcon,
  DumbbellIcon,
  HelpIcon,
  HomeIcon,
  LogoutIcon,
  MessageIcon,
  SearchIcon,
  SettingsIcon,
  UserIcon,
  UsersIcon,
} from "@/components/icons";
import { Logo } from "@/components/logo";
import { Avatar } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { now } from "@/lib/date";
import { ROLE_LABEL, type UserRole } from "@/lib/types";

type NavItem = {
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  href?: string; // no href = coming soon
};

const PROFILE: NavItem = { label: "My profile", icon: UserIcon, href: "/dashboard/profile" };

const NAV: Record<UserRole, NavItem[]> = {
  client: [
    { label: "Overview", icon: HomeIcon, href: "/dashboard" },
    { label: "My calendar", icon: CalendarIcon },
    { label: "Workout plan", icon: DumbbellIcon },
    { label: "Progress", icon: ChartIcon },
    { label: "Messages", icon: MessageIcon },
    { label: "Membership", icon: CardIcon },
    PROFILE,
  ],
  coach: [
    { label: "Overview", icon: HomeIcon, href: "/dashboard" },
    { label: "Schedule", icon: CalendarIcon },
    { label: "Clients", icon: UsersIcon },
    { label: "Programs", icon: ClipboardIcon },
    { label: "Memberships", icon: CardIcon },
    { label: "Messages", icon: MessageIcon },
    PROFILE,
  ],
};

const SEARCH_PLACEHOLDER: Record<UserRole, string> = {
  client: "Search workouts, programs, or help…",
  coach: "Search clients, workouts, or programs…",
};

const navItemClass = "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] transition";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
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

  const nav = NAV[user.role] ?? NAV.client;
  const linked = nav.filter((item) => item.href);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line bg-surface/60 px-5 py-7 lg:flex">
        <Link href="/dashboard" aria-label="GymFlow home">
          <Logo className="px-2" />
        </Link>
        <span className="mt-6 ml-2 w-fit rounded-full bg-canvas px-3 py-1 text-xs font-bold tracking-wide uppercase">
          {ROLE_LABEL[user.role] ?? user.role}
        </span>

        <nav className="mt-6 space-y-1">
          {nav.map(({ label, icon: Icon, href }) =>
            href ? (
              <Link
                key={label}
                href={href}
                aria-current={pathname === href ? "page" : undefined}
                className={`${navItemClass} ${
                  pathname === href ? "bg-lime font-bold" : "text-ink/80 hover:bg-canvas"
                }`}
              >
                <Icon />
                {label}
              </Link>
            ) : (
              <span
                key={label}
                title="Coming soon"
                className={`${navItemClass} cursor-default text-ink/40`}
              >
                <Icon />
                {label}
                <span className="ml-auto rounded-full bg-canvas px-2 py-0.5 text-[10px] font-bold tracking-wide text-muted uppercase">
                  Soon
                </span>
              </span>
            ),
          )}
        </nav>

        <div className="mt-auto space-y-1 border-t border-line pt-5">
          <span className={`${navItemClass} cursor-default text-ink/40`} title="Coming soon">
            <SettingsIcon /> Settings
          </span>
          <span className={`${navItemClass} cursor-default text-ink/40`} title="Coming soon">
            <HelpIcon /> Help
          </span>
          <button
            type="button"
            onClick={() => void logout()}
            className={`${navItemClass} text-ink/80 hover:bg-canvas`}
          >
            <LogoutIcon /> Log out
          </button>
          <p className="px-3 pt-4 text-xs text-muted">© {now().getFullYear()} GymFlow</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex items-center gap-4 px-4 py-4 sm:px-8">
          <Link href="/dashboard" className="lg:hidden" aria-label="GymFlow home">
            <Logo className="text-xl" />
          </Link>
          <label className="hidden flex-1 items-center gap-3 rounded-full bg-surface px-5 py-2.5 text-muted md:flex">
            <SearchIcon />
            <input
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted"
              placeholder={SEARCH_PLACEHOLDER[user.role] ?? SEARCH_PLACEHOLDER.client}
            />
          </label>
          <div className="ml-auto flex items-center gap-4">
            <button type="button" className="relative text-ink/80" aria-label="Notifications">
              <BellIcon width={22} height={22} />
              <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-lime-strong" />
            </button>
            <Link
              href="/dashboard/profile"
              className="flex items-center gap-3 border-l border-line pl-4"
              aria-label="My profile"
            >
              <Avatar firstName={user.first_name} lastName={user.last_name} size="sm" />
              <span className="hidden text-sm font-semibold sm:block">
                {user.first_name} {user.last_name}
              </span>
            </Link>
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

        {/* Mobile navigation */}
        <nav className="flex gap-2 overflow-x-auto px-4 pb-2 sm:px-8 lg:hidden">
          {linked.map(({ label, icon: Icon, href }) => (
            <Link
              key={label}
              href={href ?? "/dashboard"}
              className={`flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm ${
                pathname === href ? "bg-lime font-bold" : "bg-surface text-ink/80"
              }`}
            >
              <Icon width={16} height={16} />
              {label}
            </Link>
          ))}
        </nav>

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
