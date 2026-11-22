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

const FIELD_MESSAGES: Record<string, string> = {
  email: "Enter a valid email address.",
};

/** Error thrown for any failed API call. `fieldErrors` holds 422 validation messages by field. */
export class ApiError extends Error {
  readonly status: number;
  readonly fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

type ValidationIssue = { loc?: unknown[]; msg?: unknown };

function parseValidationErrors(detail: ValidationIssue[]): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const issue of detail) {
    const field = issue.loc?.at(-1);
    if (typeof field !== "string" || errors[field]) continue;
    const raw = typeof issue.msg === "string" ? issue.msg : "Invalid value.";
    errors[field] = FIELD_MESSAGES[field] ?? raw.replace(/^Value error, /, "");
  }
  return errors;
}

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
    throw new ApiError(0, UNAVAILABLE);
  }

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      // Not JSON: the API itself is unreachable (proxy error page, 404 from the host, …).
      throw new ApiError(res.status, UNAVAILABLE);
    }

    let message = res.status >= 500 ? UNAVAILABLE : `Request failed (${res.status})`;
    let fieldErrors: Record<string, string> = {};
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        fieldErrors = parseValidationErrors(detail as ValidationIssue[]);
        message = Object.values(fieldErrors)[0] ?? "Please check the highlighted fields.";
      }
    }
    throw new ApiError(res.status, message, fieldErrors);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}
