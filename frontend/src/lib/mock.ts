// Sample data for parts of the dashboard the backend doesn't serve yet
// (bookings, workouts, coach clients), plus the data used in demo mode.

import { addDays, now } from "@/lib/date";
import type { CurrentMembership, CurrentUser, UserProfile, UserRole } from "@/lib/types";

export type Session = {
  title: string;
  dayOffset: number; // 0 = Monday of the current week
  hour: number; // start hour, 24h
  minute?: number;
};

export const weeklyTarget = 4;
export const trainingStreakWeeks = 4;
export const goal = "Build strength";

export const weekSessions: Session[] = [
  { title: "Strength", dayOffset: 0, hour: 18 },
  { title: "Full Body", dayOffset: 1, hour: 18 },
  { title: "Mobility", dayOffset: 3, hour: 17, minute: 30 },
  { title: "Cardio", dayOffset: 5, hour: 10 },
];

export const todaysWorkout = {
  title: "Full Body Strength",
  duration: "60 min",
  coach: "Alex Morgan",
  exercises: [
    { name: "Squat", sets: "3 × 10" },
    { name: "Dumbbell row", sets: "3 × 12" },
    { name: "Plank", sets: "3 × 45 sec" },
  ],
};

// ---------- Coach ----------

export type CoachSession = { hour: number; title: string; client: string; minutes: number };

export const coachSchedule: CoachSession[] = [
  { hour: 9, title: "Mobility", client: "Noah Reed", minutes: 45 },
  { hour: 11, title: "Strength", client: "Mia Brooks", minutes: 60 },
  { hour: 15, title: "Progress review", client: "Liam Scott", minutes: 45 },
  { hour: 18, title: "Full Body", client: "Emma Wilson", minutes: 60 },
];

export type CoachClient = {
  name: string;
  plan: string;
  sessionsLeft: number;
  sessionsTotal: number;
  renewSoon?: boolean;
};

export const coachClients: CoachClient[] = [
  { name: "Emma Wilson", plan: "Full Body Strength", sessionsLeft: 6, sessionsTotal: 8 },
  { name: "Noah Reed", plan: "Mobility", sessionsLeft: 4, sessionsTotal: 8 },
  { name: "Mia Brooks", plan: "Cardio", sessionsLeft: 2, sessionsTotal: 8, renewSoon: true },
  { name: "Liam Scott", plan: "Strength", sessionsLeft: 5, sessionsTotal: 8 },
];

export const coachStats = { activeClients: 24, renewals: 3, attendance: 92 };

// ---------- Demo mode ----------

export const DEMO_USERS: Record<UserRole, CurrentUser> = {
  client: { id: 0, email: "emma@gymflow.app", first_name: "Emma", last_name: "Wilson", role: "client" },
  coach: { id: 0, email: "alex@gymflow.app", first_name: "Alex", last_name: "Morgan", role: "coach" },
};

export function demoProfile(user: CurrentUser): UserProfile {
  return {
    ...user,
    phone: user.role === "coach" ? "+48601234567" : "+48501234567",
    birth_date: user.role === "coach" ? "1991-06-03" : "1998-04-12",
  };
}

export function demoMembership(role: UserRole): CurrentMembership {
  const today = now();
  const coach = role === "coach";
  return {
    membership: {
      id: 0,
      status: "active",
      starts_at: addDays(today, coach ? -10 : -14).toISOString(),
      expires_at: addDays(today, coach ? 20 : 16).toISOString(),
      membership_type: {
        id: 0,
        code: coach ? "coach" : "flow-plus",
        name: coach ? "Coach Membership" : "Flow Plus",
        description: null,
        duration_days: 30,
        price: null,
        max_entries: null,
      },
    },
    has_active_coach_membership: coach,
  };
}
