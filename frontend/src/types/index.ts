export interface Course {
  id: number;
  name: string;
  course_code: string | null;
}

export interface PurgeEventResult {
  event_id: number;
  title: string | null;
  start_at: string | null;
  status: "matched" | "deleted" | "failed" | "skipped";
  match_reason?: string | null;
  error_message?: string | null;
}

export interface PurgeReport {
  course_id: number;
  course_name: string;
  dry_run: boolean;
  matched_count: number;
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
