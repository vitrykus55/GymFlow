"use client";

import { CoachOverview } from "@/components/coach-overview";
import { MemberOverview } from "@/components/member-overview";
import { Banner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { useMembership } from "@/lib/membership";

export default function OverviewPage() {
  const { user } = useAuth();
  const membership = useMembership();
  const isCoach = user?.role === "coach";
  const coachAccess = membership.data?.has_active_coach_membership ?? false;

  if (isCoach && membership.loading) {
    // Avoid flashing the member view before we know whether coach access is active.
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="size-8 animate-spin rounded-full border-4 border-line border-t-ink" />
      </div>
    );
  }

  if (isCoach && coachAccess) {
    return <CoachOverview membership={membership} />;
  }

  // Coach role without an active Coach Membership: access is paused (backend returns 403
  // on coach routes), so show the member view with an explanation.
  const notice =
    isCoach && !membership.loading ? (
      <Banner tone="warn">
        <strong>Coach tools are paused.</strong> Your Coach Membership isn&apos;t active, so
        coach features are hidden until it&apos;s renewed.
      </Banner>
    ) : null;

  return <MemberOverview membership={membership} notice={notice} />;
}
