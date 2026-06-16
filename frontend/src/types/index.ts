export interface Course {
  id: number;
  name: string;
  course_code: string | null;
}

export interface PurgeEventResult {
  event_id: number;
  title: string | null;
  start_at: string | null;
  html_url?: string | null;
  status: "matched" | "deleted" | "failed" | "skipped";
  event_category?: "fbf" | "user";
  user_event_kind?: "calendar_event" | "appointment_group" | null;
  calendar_entry_kind?: "calendar_event" | "assignment_due";
  match_reason?: string | null;
  error_message?: string | null;
  link_status?: "orphan" | "linked" | "unlinked" | "unknown" | null;
  link_reason?: string | null;
  canvas_assignment_id?: number | null;
  assignment_due_at?: string | null;
  appointment_group_id?: number | null;
}

export interface PurgeReport {
  course_id: number;
  course_name: string;
  dry_run: boolean;
  matched_count: number;
  orphan_count: number;
  user_count?: number;
  deleted_count: number;
  failed_count: number;
  events: PurgeEventResult[];
  started_at: string;
  finished_at: string | null;
  preview_token: string | null;
}

export interface AuthMe {
  authenticated: boolean;
  user_name?: string;
}

export interface ApiError {
  detail: string;
  code?: string;
}
