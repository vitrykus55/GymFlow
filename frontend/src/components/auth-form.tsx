"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { DumbbellIcon, UsersIcon } from "@/components/icons";
import { Logo } from "@/components/logo";
import { Field, primaryButton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { now, toDateInput } from "@/lib/date";

type Mode = "login" | "register";

type FormState = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone: string;
  birth_date: string;
};

type FieldName = keyof FormState;

const EMPTY: FormState = {
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  phone: "",
  birth_date: "",
};

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const { status, login, register, startDemo } = useAuth();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [today] = useState(() => toDateInput(now()));

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  const set = (key: FieldName) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((errs) => ({ ...errs, [key]: undefined }));
  };

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setErrors({});
    try {
      if (mode === "register") {
        await register(form);
      } else {
        await login(form.email, form.password);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setErrors({ email: "An account with this email already exists." });
      } else if (err instanceof ApiError && Object.keys(err.fieldErrors).length > 0) {
        setErrors(err.fieldErrors);
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      }
    } finally {
      setBusy(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <section className="relative hidden flex-col justify-between overflow-hidden bg-night p-12 text-white lg:flex">
        <Logo />
        <div>
          <h1 className="text-5xl leading-tight font-extrabold tracking-tight">
            Train with a plan.
            <br />
            <span className="text-lime">Stay in flow.</span>
          </h1>
          <p className="mt-5 max-w-md text-white/60">
            Book sessions, track your membership and follow your workouts — all in one place.
          </p>
          <ul className="mt-10 grid max-w-md gap-3 text-sm">
            <li className="flex items-start gap-3 rounded-2xl bg-white/5 p-4 ring-1 ring-white/10">
              <DumbbellIcon className="mt-0.5 shrink-0 text-lime" />
              <span>
                <strong className="block text-white">Members</strong>
                <span className="text-white/60">Your calendar, workouts and membership.</span>
              </span>
            </li>
            <li className="flex items-start gap-3 rounded-2xl bg-white/5 p-4 ring-1 ring-white/10">
              <UsersIcon className="mt-0.5 shrink-0 text-lime" />
              <span>
                <strong className="block text-white">Coaches</strong>
                <span className="text-white/60">
                  Clients and schedule — unlocked with an active Coach Membership.
                </span>
              </span>
            </li>
          </ul>
        </div>
        <p className="text-sm text-white/40">© {now().getFullYear()} GymFlow</p>
        <div className="pointer-events-none absolute -right-24 -bottom-24 size-96 rounded-full bg-lime/10 blur-3xl" />
      </section>

      {/* Form */}
      <section className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <Logo className="mb-10 lg:hidden" />
          <h2 className="text-3xl font-extrabold tracking-tight">
            {isRegister ? "Create your account" : "Welcome back"}
          </h2>
          <p className="mt-2 text-muted">
            {isRegister ? "Start training with GymFlow today." : "Log in to continue your training."}
          </p>

          <form className="mt-8 space-y-4" onSubmit={onSubmit}>
            {isRegister && (
              <div className="grid grid-cols-2 gap-3">
                <Field
                  label="First name"
                  autoComplete="given-name"
                  maxLength={100}
                  required
                  value={form.first_name}
                  onChange={set("first_name")}
                  error={errors.first_name}
                />
                <Field
                  label="Last name"
                  autoComplete="family-name"
                  maxLength={100}
                  required
                  value={form.last_name}
                  onChange={set("last_name")}
                  error={errors.last_name}
                />
              </div>
            )}
            <Field
              label="Email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              required
              value={form.email}
              onChange={set("email")}
              error={errors.email}
            />
            {isRegister && (
              <div className="grid gap-3 sm:grid-cols-2">
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
                  hint="With country code"
                />
                <Field
                  label={
                    <>
                      Date of birth <span className="font-normal text-muted">(optional)</span>
                    </>
                  }
                  type="date"
                  autoComplete="bday"
                  max={today}
                  value={form.birth_date}
                  onChange={set("birth_date")}
                  error={errors.birth_date}
                />
              </div>
            )}
            <Field
              label="Password"
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              minLength={8}
              maxLength={128}
              required
              value={form.password}
              onChange={set("password")}
              error={errors.password}
              hint={isRegister ? "At least 8 characters." : undefined}
            />

            {error && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
                {error}
              </p>
            )}

            <button type="submit" disabled={busy} className={`${primaryButton} w-full py-3.5`}>
              {busy ? "Please wait…" : isRegister ? "Create account" : "Log in"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted">
            {isRegister ? "Already have an account? " : "New to GymFlow? "}
            <Link
              href={isRegister ? "/login" : "/register"}
              className="font-bold text-ink underline-offset-4 hover:underline"
            >
              {isRegister ? "Log in" : "Create an account"}
            </Link>
          </p>

          <div className="mt-8 border-t border-line pt-6 text-center">
            <p className="text-xs font-semibold tracking-wide text-muted uppercase">
              Just looking around?
            </p>
            <div className="mt-3 flex justify-center gap-2">
              <button
                type="button"
                onClick={() => startDemo("client")}
                className="rounded-full bg-surface px-4 py-2 text-sm font-semibold ring-1 ring-line hover:ring-ink"
              >
                Member demo
              </button>
              <button
                type="button"
                onClick={() => startDemo("coach")}
                className="rounded-full bg-surface px-4 py-2 text-sm font-semibold ring-1 ring-line hover:ring-ink"
              >
                Coach demo
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
