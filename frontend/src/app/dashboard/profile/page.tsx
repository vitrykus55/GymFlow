"use client";

import { useEffect, useState, type FormEvent } from "react";

import { CheckIcon } from "@/components/icons";
import { MembershipCard } from "@/components/membership-card";
import { Avatar, Banner, Field, primaryButton, secondaryButton, Skeleton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, now, toDateInput } from "@/lib/date";
import { useMembership } from "@/lib/membership";
import { DEMO_USERS, demoProfile } from "@/lib/mock";
import { ROLE_LABEL, type ProfileUpdate, type UserProfile } from "@/lib/types";

type FormState = {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  birth_date: string;
};

type FieldName = keyof FormState;

function toForm(p: UserProfile): FormState {
  return {
    first_name: p.first_name,
    last_name: p.last_name,
    email: p.email,
    phone: p.phone ?? "",
    birth_date: p.birth_date ?? "",
  };
}

/** Only the fields that differ from the saved profile, in the shape PATCH /users/me expects. */
function diff(form: FormState, saved: UserProfile): ProfileUpdate {
  const patch: ProfileUpdate = {};
  const first = form.first_name.trim();
  const last = form.last_name.trim();
  const email = form.email.trim().toLowerCase();
  const phone = form.phone.trim() || null;
  const birth = form.birth_date || null;
  if (first !== saved.first_name) patch.first_name = first;
  if (last !== saved.last_name) patch.last_name = last;
  if (email !== saved.email) patch.email = email;
  if (phone !== saved.phone) patch.phone = phone;
  if (birth !== saved.birth_date) patch.birth_date = birth;
  return patch;
}

export default function ProfilePage() {
  const { authFetch, isDemo, user, updateUser } = useAuth();
  const membership = useMembership();
  const role = user?.role ?? "client";

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [loadError, setLoadError] = useState("");
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [today] = useState(() => toDateInput(now()));

  useEffect(() => {
    let cancelled = false;
    const load = isDemo
      ? Promise.resolve(demoProfile(DEMO_USERS[role]))
      : authFetch<UserProfile>("/api/v1/users/me");
    load
      .then((p) => {
        if (cancelled) return;
        setProfile(p);
        setForm(toForm(p));
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : "Could not load profile.");
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, isDemo, role]);

  const patch = profile && form ? diff(form, profile) : {};
  const dirty = Object.keys(patch).length > 0;

  const set = (key: FieldName) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setForm((f) => (f ? { ...f, [key]: value } : f));
    setErrors((errs) => ({ ...errs, [key]: undefined }));
    setSaved(false);
  };

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!profile || !dirty) return;
    setSaving(true);
    setErrors({});
    setFormError("");
    try {
      const updated = isDemo
        ? { ...profile, ...patch }
        : await authFetch<UserProfile>("/api/v1/users/me", {
            method: "PATCH",
            body: JSON.stringify(patch),
          });
      setProfile(updated);
      setForm(toForm(updated));
      updateUser({
        first_name: updated.first_name,
        last_name: updated.last_name,
        email: updated.email,
      });
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setErrors({ email: "This email is already used by another account." });
      } else if (err instanceof ApiError && Object.keys(err.fieldErrors).length > 0) {
        setErrors(err.fieldErrors);
      } else {
        setFormError(err instanceof Error ? err.message : "Something went wrong.");
      }
    } finally {
      setSaving(false);
    }
  }

  function discard() {
    if (!profile) return;
    setForm(toForm(profile));
    setErrors({});
    setFormError("");
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">My profile</h1>
        <p className="mt-2 text-lg text-muted">Keep your personal details up to date.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        {/* Personal details */}
        <form
          onSubmit={onSubmit}
          className="rounded-3xl border border-line bg-surface p-5 sm:p-8"
        >
          <h2 className="text-2xl font-extrabold tracking-tight">Personal details</h2>
          <p className="mt-1 text-sm text-muted">
            This is how coaches and the front desk will see you.
          </p>

          {loadError ? (
            <div className="mt-6">
              <Banner tone="warn">{loadError}</Banner>
            </div>
          ) : !form ? (
            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              {Array.from({ length: 5 }, (_, i) => (
                <div key={i} className={i === 2 ? "sm:col-span-2" : ""}>
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="mt-2 h-11 w-full" />
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <Field
                label="First name"
                autoComplete="given-name"
                required
                maxLength={100}
                value={form.first_name}
                onChange={set("first_name")}
                error={errors.first_name}
              />
              <Field
                label="Last name"
                autoComplete="family-name"
                required
                maxLength={100}
                value={form.last_name}
                onChange={set("last_name")}
                error={errors.last_name}
              />
              <Field
                className="sm:col-span-2"
                label="Email"
                type="email"
                autoComplete="email"
                required
                value={form.email}
                onChange={set("email")}
                error={errors.email}
              />
              <Field
                label={
                  <>
                    Phone <span className="font-normal text-muted">(optional)</span>
                  </>
                }
                type="tel"
                autoComplete="tel"
                placeholder="+48 501 234 567"
                maxLength={30}
                value={form.phone}
                onChange={set("phone")}
                error={errors.phone}
                hint="Include the country code. Leave empty to remove."
              />
              <Field
                label={
                  <>
                    Date of birth <span className="font-normal text-muted">(optional)</span>
                  </>
                }
                type="date"
                max={today}
                value={form.birth_date}
                onChange={set("birth_date")}
                error={errors.birth_date}
              />
            </div>
          )}

          {formError && (
            <p className="mt-6 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
              {formError}
            </p>
          )}

          <div className="mt-8 flex flex-wrap items-center justify-end gap-3 border-t border-line pt-6">
            <p className="mr-auto text-sm" role="status">
              {saved && !dirty ? (
                <span className="flex items-center gap-1.5 font-semibold text-ink">
                  <span className="grid size-5 place-items-center rounded-full bg-lime">
                    <CheckIcon width={12} height={12} strokeWidth={3} />
                  </span>
                  Changes saved{isDemo ? " (demo only)" : ""}
                </span>
              ) : dirty ? (
                <span className="text-muted">You have unsaved changes.</span>
              ) : null}
            </p>
            <button type="button" onClick={discard} disabled={!dirty || saving} className={secondaryButton}>
              Discard
            </button>
            <button type="submit" disabled={!dirty || saving} className={primaryButton}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>

        {/* Account summary */}
        <aside className="space-y-6">
          <section className="rounded-3xl border border-line bg-surface p-6">
            <div className="flex items-center gap-4">
              <Avatar
                firstName={profile?.first_name ?? user?.first_name ?? ""}
                lastName={profile?.last_name ?? user?.last_name ?? ""}
                size="lg"
              />
              <div className="min-w-0">
                <p className="truncate text-2xl font-extrabold">
                  {profile?.first_name ?? user?.first_name} {profile?.last_name ?? user?.last_name}
                </p>
                <p className="truncate text-sm text-muted">{profile?.email ?? user?.email}</p>
                <span className="mt-2 inline-block rounded-full bg-canvas px-3 py-1 text-xs font-bold tracking-wide uppercase">
                  {ROLE_LABEL[role] ?? role}
                </span>
              </div>
            </div>
            <dl className="mt-5 divide-y divide-line text-sm">
              <div className="flex justify-between py-3">
                <dt className="text-muted">Phone</dt>
                <dd className="font-semibold">{profile?.phone ?? "—"}</dd>
              </div>
              <div className="flex justify-between py-3">
                <dt className="text-muted">Date of birth</dt>
                <dd className="font-semibold">
                  {profile?.birth_date ? formatDate(`${profile.birth_date}T00:00:00`) : "—"}
                </dd>
              </div>
              {role === "coach" && (
                <div className="flex justify-between py-3">
                  <dt className="text-muted">Coach access</dt>
                  <dd className="font-semibold">
                    {membership.loading
                      ? "…"
                      : membership.data?.has_active_coach_membership
                        ? "Active"
                        : "Paused"}
                  </dd>
                </div>
              )}
            </dl>
            <p className="mt-3 text-xs text-muted">
              Your role comes from your membership and can&apos;t be changed here.
            </p>
          </section>

          <MembershipCard
            {...membership}
            title={role === "coach" ? "Coach membership" : "Your membership"}
          />
        </aside>
      </div>
    </div>
  );
}
