"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { Logo } from "@/components/logo";
import { useAuth } from "@/lib/auth";

type Mode = "login" | "register";

const inputClass =
  "mt-1.5 w-full rounded-xl border border-line bg-white px-4 py-3 text-sm outline-none transition placeholder:text-muted/60 focus:border-ink focus:ring-4 focus:ring-lime/60";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const { status, login, register, startDemo } = useAuth();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "register") {
        await register(form);
      } else {
        await login(form.email, form.password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
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
        </div>
        <div className="flex gap-10 text-sm text-white/60">
          <div>
            <p className="text-2xl font-bold text-white">8</p>sessions / month
          </div>
          <div>
            <p className="text-2xl font-bold text-white">24/7</p>gym access
          </div>
          <div>
            <p className="text-2xl font-bold text-white">1:1</p>coaching
          </div>
        </div>
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
            {isRegister ? "Start your GymFlow membership today." : "Log in to continue your training."}
          </p>

          <form className="mt-8 space-y-4" onSubmit={onSubmit}>
            {isRegister && (
              <div className="grid grid-cols-2 gap-3">
                <label className="block text-sm font-semibold">
                  First name
                  <input
                    className={inputClass}
                    autoComplete="given-name"
                    maxLength={100}
                    required
                    value={form.first_name}
                    onChange={set("first_name")}
                  />
                </label>
                <label className="block text-sm font-semibold">
                  Last name
                  <input
                    className={inputClass}
                    autoComplete="family-name"
                    maxLength={100}
                    required
                    value={form.last_name}
                    onChange={set("last_name")}
                  />
                </label>
              </div>
            )}
            <label className="block text-sm font-semibold">
              Email
              <input
                className={inputClass}
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
                value={form.email}
                onChange={set("email")}
              />
            </label>
            {isRegister && (
              <label className="block text-sm font-semibold">
                Phone <span className="font-normal text-muted">(optional)</span>
                <input
                  className={inputClass}
                  type="tel"
                  autoComplete="tel"
                  maxLength={30}
                  value={form.phone}
                  onChange={set("phone")}
                />
              </label>
            )}
            <label className="block text-sm font-semibold">
              Password
              <input
                className={inputClass}
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                placeholder={isRegister ? "At least 8 characters" : undefined}
                minLength={8}
                maxLength={128}
                required
                value={form.password}
                onChange={set("password")}
              />
            </label>

            {error && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-full bg-ink py-3.5 text-sm font-bold text-white transition hover:bg-black disabled:opacity-60"
            >
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
            <button
              type="button"
              onClick={startDemo}
              className="text-sm font-semibold text-muted underline-offset-4 hover:text-ink hover:underline"
            >
              Explore the demo dashboard →
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
