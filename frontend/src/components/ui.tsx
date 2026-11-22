"use client";

import { useId, useState, type InputHTMLAttributes, type ReactNode } from "react";

import { AlertIcon, EyeIcon, EyeOffIcon } from "@/components/icons";

export const inputClass =
  "mt-1.5 w-full rounded-xl border bg-white px-4 py-3 text-sm outline-none transition placeholder:text-muted/60 focus:border-ink focus:ring-4 focus:ring-lime/60 disabled:bg-canvas disabled:text-muted";

export const primaryButton =
  "inline-flex items-center justify-center gap-2 rounded-full bg-ink px-6 py-3 text-sm font-bold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-50";

export const secondaryButton =
  "inline-flex items-center justify-center gap-2 rounded-full bg-canvas px-6 py-3 text-sm font-bold text-ink transition hover:bg-line disabled:cursor-not-allowed disabled:opacity-50";

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: ReactNode;
  error?: string;
  hint?: ReactNode;
};

/** Labelled input with an optional hint and an inline validation error. */
export function Field({ label, error, hint, className = "", type, ...input }: FieldProps) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const isPassword = type === "password";
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-semibold">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={isPassword && visible ? "text" : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={`${inputClass} ${error ? "border-red-400" : "border-line"} ${isPassword ? "pr-12" : ""}`}
          {...input}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? "Hide password" : "Show password"}
            className="absolute top-1/2 right-3 mt-0.5 -translate-y-1/2 rounded-lg p-1.5 text-muted hover:text-ink"
          >
            {visible ? <EyeOffIcon width={18} height={18} /> : <EyeIcon width={18} height={18} />}
          </button>
        )}
      </div>
      {error ? (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-red-600">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function Avatar({
  firstName,
  lastName,
  size = "md",
}: {
  firstName: string;
  lastName: string;
  size?: "sm" | "md" | "lg";
}) {
  const initials = `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
  const sizes = { sm: "size-10 text-sm", md: "size-16 text-xl", lg: "size-24 text-3xl" };
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-full bg-ink font-bold text-lime ${sizes[size]}`}
    >
      {initials}
    </span>
  );
}

export function Banner({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  const tones = {
    info: "bg-lime/40 text-ink",
    warn: "bg-amber-50 text-amber-900 ring-1 ring-amber-200",
  };
  return (
    <div className={`flex items-start gap-3 rounded-2xl px-4 py-3 text-sm ${tones[tone]}`}>
      <AlertIcon width={18} height={18} className="mt-0.5 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-line/70 ${className}`} />;
}
