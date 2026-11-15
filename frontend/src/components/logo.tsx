export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`flex items-center gap-2 text-2xl font-extrabold tracking-tight ${className}`}>
      <svg width="30" height="20" viewBox="0 0 30 20" aria-hidden="true">
        <path d="M2 18 L14 6 L20 6 L8 18 Z" fill="var(--color-lime-strong)" />
        <path d="M12 18 L26 4 L29 4 L15 18 Z" fill="var(--color-lime-strong)" opacity="0.6" />
      </svg>
      GymFlow
    </span>
  );
}
