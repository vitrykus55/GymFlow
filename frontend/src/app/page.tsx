import { apiFetch } from "@/lib/api";

// Render on every request so the backend status is live (and the build doesn't need the API).
export const dynamic = "force-dynamic";

type Health = { status: string; service: string; version: string };

async function getBackendHealth(): Promise<Health | null> {
  try {
    return await apiFetch<Health>("/api/v1/health", { cache: "no-store" });
  } catch {
    return null;
  }
}

export default async function Home() {
  const health = await getBackendHealth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-5xl font-bold tracking-tight">GymFlow</h1>
      <p className="text-lg opacity-70">Next.js + FastAPI</p>

      <div className="rounded-xl border border-black/10 px-6 py-4 dark:border-white/15">
        <span className="font-mono text-sm">Backend: </span>
        {health ? (
          <span className="font-mono text-sm text-green-600">
            {health.status} (v{health.version})
          </span>
        ) : (
          <span className="font-mono text-sm text-red-600">unavailable</span>
        )}
      </div>
    </main>
  );
}
