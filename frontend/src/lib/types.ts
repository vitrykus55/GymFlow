// Shapes returned by the FastAPI backend (see backend/README.md).

export type UserRole = "client" | "coach";

export type CurrentUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
};

export type UserProfile = CurrentUser & {
  phone: string | null;
  birth_date: string | null; // YYYY-MM-DD
};

export type ProfileUpdate = Partial<{
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  birth_date: string | null;
}>;

export type MembershipStatus = "pending" | "active" | "expired" | "cancelled";

export type MembershipType = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  duration_days: number | null;
  price: string | null;
  max_entries: number | null;
};

export type UserMembership = {
  id: number;
  status: MembershipStatus;
  starts_at: string;
  expires_at: string;
  membership_type: MembershipType;
};

export type CurrentMembership = {
  membership: UserMembership | null;
  has_active_coach_membership: boolean;
};

export const ROLE_LABEL: Record<UserRole, string> = {
  client: "Member",
  coach: "Coach",
};
