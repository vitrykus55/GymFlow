// Sample data for the member dashboard until the backend exposes
// memberships, bookings and workouts endpoints.

export type Session = {
  title: string;
  dayOffset: number; // 0 = Monday of the current week
  hour: number; // start hour, 24h
  minute?: number;
};

export const weeklyTarget = 3;
export const trainingStreakWeeks = 4;
export const goal = "Build strength";

export const membership = {
  plan: "Flow Plus",
  sessionsTotal: 8,
  sessionsLeft: 6,
  renewsInDays: 16,
};

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
