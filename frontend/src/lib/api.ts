/**
 * Base URL of the FastAPI backend.
 * - In the browser we use relative URLs: Next.js rewrites /api/v1/* to the backend
 *   (see next.config.ts), so auth cookies are same-origin.
 * - On the server we call the backend directly.
 */
export function getApiUrl(): string {
  if (typeof window === "undefined") {
    return process.env.API_INTERNAL_URL ?? "http://localhost:8000";
  }
  return "";
}

const UNAVAILABLE = "Server is unavailable. Please try again later.";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(`${getApiUrl()}${path}`, {
      ...init,
      credentials: init?.credentials ?? "include",
      headers,
    });
  } catch {
    throw new Error(UNAVAILABLE);
  }

  if (!res.ok) {
    let message = res.status >= 500 ? UNAVAILABLE : `Request failed (${res.status})`;
    try {
      const body: unknown = await res.json();
      if (typeof body === "object" && body !== null && "detail" in body) {
        const detail = body.detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
          // FastAPI validation error (422)
          message = detail[0].msg;
        }
      }
    } catch {
      // Keep the status-based message when the server does not return JSON.
    }
    throw new Error(message);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}
