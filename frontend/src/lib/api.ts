import type { ApiError, AuthMe, Course, PurgeEventResult, PurgeReport } from "@/types";

/** Server-side / build-time only. Browser uses same-origin `/api/*` via Next.js rewrite. */
const SERVER_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

function apiUrl(path: string): string {
  if (typeof window !== "undefined") {
    return path;
  }
  return `${SERVER_BACKEND_URL}${path}`;
}

const USER_MESSAGES: Record<number, string> = {
  401: "Please sign in with Canvas again.",
  403: "You don't have permission to manage this course's calendar.",
  409: "The course calendar changed. Please review the list again.",
  429: "Canvas is busy. Wait a moment and try again.",
  502: "Canvas API error.",
  500: "Server error.",
};

export class ApiRequestError extends Error {
  status: number;
  code?: string;

  constructor(status: number, detail: string, code?: string) {
    super(`[${status}] ${detail}`);
    this.status = status;
    this.code = code;
  }

  /** Message without the [status] prefix for compact UI display. */
  get detail(): string {
    return this.message.replace(/^\[\d+\]\s*/, "");
  }
}

function formatDetail(body: unknown): string | undefined {
  if (!body || typeof body !== "object") return undefined;
  const record = body as Record<string, unknown>;
  if (typeof record.detail === "string") return record.detail;
  if (Array.isArray(record.detail)) {
    return record.detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return String(item);
      })
      .join("; ");
  }
  if (typeof record.message === "string") return record.message;
  return undefined;
}

async function parseError(response: Response): Promise<ApiRequestError> {
  const text = await response.text();
  let detail =
    USER_MESSAGES[response.status] ?? `Request failed (HTTP ${response.status})`;
  let code: string | undefined;

  try {
    const body = JSON.parse(text) as ApiError;
    detail = formatDetail(body) ?? detail;
    code = body.code;
  } catch {
    const trimmed = text.trim();
    if (trimmed && !trimmed.startsWith("<!") && trimmed.length < 800) {
      detail = trimmed;
    }
  }

  return new ApiRequestError(response.status, detail, code);
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = apiUrl(path);
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (err) {
    const msg =
      err instanceof Error
        ? err.message
        : "Network error — is the backend running on port 8000?";
    throw new ApiRequestError(0, msg);
  }

  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function getLoginUrl(): string {
  return "/api/auth/login";
}

/** Returns false if the Next.js API proxy cannot reach the Python backend. */
export async function checkBackendReachable(): Promise<boolean> {
  try {
    const response = await fetch(apiUrl("/api/auth/me"), { credentials: "include" });
    return response.ok || response.status === 401;
  } catch {
    return false;
  }
}

export async function getMe(): Promise<AuthMe> {
  return apiFetch<AuthMe>("/api/auth/me");
}

export interface AuthConfig {
  oauth_enabled: boolean;
  token_login_enabled: boolean;
  dev_fallback: boolean;
  canvas_base_url: string;
}

export async function getAuthConfig(): Promise<AuthConfig> {
  return apiFetch<AuthConfig>("/api/auth/config");
}

export interface VisitorStats {
  lifetime_users: number;
}

export async function registerVisitor(): Promise<VisitorStats> {
  return apiFetch<VisitorStats>("/api/stats/visitors");
}

export async function loginWithAccessToken(accessToken: string): Promise<AuthMe> {
  return apiFetch<AuthMe>("/api/auth/token", {
    method: "POST",
    body: JSON.stringify({ access_token: accessToken }),
  });
}

export async function logout(): Promise<void> {
  await apiFetch("/api/auth/logout", { method: "POST" });
}

export async function listCourses(): Promise<Course[]> {
  const data = await apiFetch<{ courses: Course[] }>("/api/courses");
  return data.courses;
}

export async function previewPurge(courseId: number): Promise<PurgeReport> {
  return apiFetch<PurgeReport>(`/api/courses/${courseId}/purge/preview`);
}

export async function executePurge(
  courseId: number,
  eventIds: number[],
  previewToken: string,
): Promise<PurgeReport> {
  return apiFetch<PurgeReport>(`/api/courses/${courseId}/purge`, {
    method: "POST",
    headers: { "X-Confirm-Course-Id": String(courseId) },
    body: JSON.stringify({
      confirm: true,
      event_ids: eventIds,
      preview_token: previewToken,
    }),
  });
}

export function downloadReportCsv(report: PurgeReport, filename: string): void {
  const headers = [
    "event_id",
    "title",
    "start_at",
    "html_url",
    "event_category",
    "link_status",
    "canvas_assignment_id",
    "status",
    "error_message",
  ];
  const rows = report.events.map((e) =>
    [
      e.event_id,
      `"${(e.title ?? "").replace(/"/g, '""')}"`,
      e.start_at ?? "",
      e.html_url ?? "",
      e.event_category ?? "fbf",
      e.link_status ?? "",
      e.canvas_assignment_id ?? "",
      e.status,
      `"${(e.error_message ?? "").replace(/"/g, '""')}"`,
    ].join(","),
  );
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function formatEventDate(iso: string | null): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "—";
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(iso);
  if (dateOnly) {
    return parsed.toLocaleDateString(undefined, { dateStyle: "medium" });
  }
  return parsed.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function isPastEvent(startAt: string | null): boolean {
  if (!startAt) return false;
  return new Date(startAt).getTime() < Date.now();
}

/** Past filter: orphans always show; no-link/assignment-due use assignment due date when available. */
export function shouldShowWithPastFilter(
  event: Pick<
    PurgeEventResult,
    "link_status" | "start_at" | "assignment_due_at" | "calendar_entry_kind"
  >,
  pastOnly: boolean,
): boolean {
  if (!pastOnly) return true;
  if (event.link_status === "orphan") return true;
  const dateForFilter =
    event.link_status === "unlinked" || event.calendar_entry_kind === "assignment_due"
      ? (event.assignment_due_at ?? event.start_at)
      : event.start_at;
  return isPastEvent(dateForFilter);
}

export function isAssignmentDueEntry(
  event: Pick<PurgeEventResult, "calendar_entry_kind">,
): boolean {
  return event.calendar_entry_kind === "assignment_due";
}

export function formatApiError(err: unknown): string {
  if (err instanceof ApiRequestError) return err.message;
  if (err instanceof Error) return err.message;
  return "Unknown error";
}
