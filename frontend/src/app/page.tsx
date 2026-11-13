import { apiFetch } from "@/lib/api";
import { AuthPanel } from "./auth-panel";

// Render on every request so the backend status is live (and the build doesn't need the API).
export const dynamic = "force-dynamic";

type Health = { status: string; service: string; version: string };
type DatabaseHealth = { status: string; database: string };

async function getHealth<T>(path: string): Promise<T | null> {
  try {
    return await apiFetch<T>(path, { cache: "no-store" });
  } catch {
    return null;
  }
}

export default async function Home() {
  const [health, database] = await Promise.all([
    getHealth<Health>("/api/v1/health"),
    getHealth<DatabaseHealth>("/api/v1/health/db"),
  ]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <header className="text-center">
        <h1 className="text-5xl font-bold tracking-tight">GymFlow</h1>
        <p className="mt-2 text-lg opacity-70">Next.js + FastAPI + Neon PostgreSQL</p>
      </header>

      <div className="flex flex-wrap justify-center gap-3">
        <HealthBadge
          label="Backend"
          detail={health ? `${health.status} (v${health.version})` : "недоступен"}
          healthy={health !== null}
        />
        <HealthBadge
          label="Neon"
          detail={database ? "подключена" : "нет подключения"}
          healthy={database !== null}
        />
      </div>

      <AuthPanel />
    </main>
  );
}

function HealthBadge({
  label,
  detail,
  healthy,
}: {
  label: string;
  detail: string;
  healthy: boolean;
}) {
  return (
    <div className="rounded-xl border border-black/10 px-4 py-3 dark:border-white/15">
      <span className="font-mono text-sm">{label}: </span>
      <span className={`font-mono text-sm ${healthy ? "text-green-600" : "text-red-600"}`}>
        {detail}
      </span>
    </div>
  );
}
