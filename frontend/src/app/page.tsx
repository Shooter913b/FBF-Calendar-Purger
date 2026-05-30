"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { EventTable } from "@/components/EventTable";
import { EmbedVideo } from "@/components/EmbedVideo";
import { ScanSlowNotice } from "@/components/ScanSlowNotice";
import { SignInPanel } from "@/components/SignInPanel";
import {
  ApiRequestError,
  type AuthConfig,
  checkBackendReachable,
  downloadReportCsv,
  executePurge,
  formatApiError,
  getAuthConfig,
  getMe,
  listCourses,
  logout,
  previewPurge,
} from "@/lib/api";
import { MAIN_VIDEO_URL } from "@/lib/videoEmbed";
import type { Course, PurgeReport } from "@/types";

export default function HomePage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <PurgeTool />
    </Suspense>
  );
}

function PurgeTool() {
  const searchParams = useSearchParams();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [userName, setUserName] = useState<string | null>(null);

  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState("");
  const [preview, setPreview] = useState<PurgeReport | null>(null);
  const [result, setResult] = useState<PurgeReport | null>(null);

  const [loadingCourses, setLoadingCourses] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [showMainVideo, setShowMainVideo] = useState(Boolean(MAIN_VIDEO_URL?.trim()));
  const [showSlowScanNotice, setShowSlowScanNotice] = useState(false);

  const authError = searchParams.get("auth_error");

  const loadCourses = useCallback(async () => {
    setLoadingCourses(true);
    setError(null);
    try {
      const list = await listCourses();
      setCourses(list);
      const fromUrl = searchParams.get("course");
      if (fromUrl && list.some((c) => String(c.id) === fromUrl)) {
        setCourseId(fromUrl);
      } else if (list.length === 1) {
        setCourseId(String(list[0].id));
      }
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 401) {
        setAuthed(false);
      } else {
        setError(formatApiError(err));
      }
    } finally {
      setLoadingCourses(false);
    }
  }, [searchParams]);

  useEffect(() => {
    getAuthConfig()
      .then(setAuthConfig)
      .catch(() => setAuthConfig(null));
  }, []);

  const handleSignedIn = useCallback(() => {
    getMe()
      .then((me) => {
        setAuthed(me.authenticated);
        setUserName(me.user_name ?? null);
        if (me.authenticated) loadCourses();
      })
      .catch(() => setAuthed(false));
  }, [loadCourses]);

  useEffect(() => {
    getMe()
      .then((me) => {
        setAuthed(me.authenticated);
        setUserName(me.user_name ?? null);
        setBackendUp(true);
        if (me.authenticated) loadCourses();
      })
      .catch(() => {
        checkBackendReachable().then((up) => {
          setBackendUp(up);
          setAuthed(false);
        });
      });
  }, [loadCourses]);

  useEffect(() => {
    if (!scanning) {
      setShowSlowScanNotice(false);
      return;
    }
    const timer = window.setTimeout(() => setShowSlowScanNotice(true), 10_000);
    return () => window.clearTimeout(timer);
  }, [scanning]);

  const handleScan = async () => {
    const id = Number(courseId);
    if (!id) return;
    setShowMainVideo(false);
    setShowSlowScanNotice(false);
    setScanning(true);
    setError(null);
    setPreview(null);
    setResult(null);
    setSelectedIds(new Set());
    try {
      const report = await previewPurge(id);
      setPreview(report);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setScanning(false);
    }
  };

  const toggleEvent = (eventId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) next.delete(eventId);
      else next.add(eventId);
      return next;
    });
  };

  const selectAllEvents = () => {
    if (!preview) return;
    setSelectedIds(new Set(preview.events.map((e) => e.event_id)));
  };

  const clearSelection = () => setSelectedIds(new Set());

  const handleDelete = async () => {
    if (!preview?.preview_token) return;
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    if (
      !window.confirm(
        `Delete ${ids.length} selected Feedback Fruits calendar event${ids.length === 1 ? "" : "s"}?`,
      )
    ) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      const report = await executePurge(preview.course_id, ids, preview.preview_token);
      setResult(report);
      setPreview(null);
      setSelectedIds(new Set());
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setDeleting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setAuthed(false);
    setUserName(null);
    setCourses([]);
    setCourseId("");
    setPreview(null);
    setResult(null);
  };

  const displayReport = result ?? preview;

  if (authed === null) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }

  if (!authed) {
    return (
      <SignInPanel
        authConfig={authConfig}
        authError={authError}
        backendUp={backendUp}
        onSignedIn={handleSignedIn}
      />
    );
  }

  return (
    <div className="space-y-6">
      <ScanSlowNotice
        open={showSlowScanNotice && scanning}
        onDismiss={() => setShowSlowScanNotice(false)}
      />

      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">FBF Calendar Purger</h1>
        <div className="flex items-center gap-3 text-sm text-slate-600">
          {userName && <span>{userName}</span>}
          <button type="button" onClick={handleLogout} className="underline hover:text-slate-900">
            Sign out
          </button>
        </div>
      </div>

      {showMainVideo && (
        <EmbedVideo url={MAIN_VIDEO_URL} title="How to use FBF Calendar Purger" />
      )}

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-[280px] flex-1 flex-col gap-1 text-sm">
          <span className="font-medium">Course</span>
          <select
            value={courseId}
            onChange={(e) => {
              setCourseId(e.target.value);
              setPreview(null);
              setResult(null);
              setSelectedIds(new Set());
            }}
            disabled={loadingCourses}
            className="rounded border border-slate-300 px-3 py-2"
          >
            <option value="">Select a course…</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.course_code ? `${c.course_code} — ` : ""}
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={handleScan}
          disabled={!courseId || scanning}
          className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:bg-slate-400"
        >
          {scanning ? "Scanning…" : "Scan"}
        </button>
      </div>

      {error && (
        <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {result && (
        <p className="rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          Deleted {result.deleted_count} event{result.deleted_count === 1 ? "" : "s"}.
          {result.failed_count > 0 && ` ${result.failed_count} failed.`}
        </p>
      )}

      {preview && !result && (
        <p className="text-sm text-slate-600">
          {preview.matched_count === 0
            ? "No Feedback Fruits calendar events found."
            : `Found ${preview.matched_count} event${preview.matched_count === 1 ? "" : "s"}. Click rows to select which to delete.`}
          {preview.matched_count > 0 && (
            <span className="ml-2 text-slate-500">
              ({selectedIds.size} selected)
            </span>
          )}
        </p>
      )}

      {displayReport && displayReport.events.length > 0 && (
        <>
          {preview && !result && preview.matched_count > 0 && (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={selectAllEvents}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
              >
                Select all
              </button>
              <button
                type="button"
                onClick={clearSelection}
                disabled={selectedIds.size === 0}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-40"
              >
                Clear selection
              </button>
            </div>
          )}
          <EventTable
            events={displayReport.events}
            showStatus={!!result}
            selectable={!!preview && !result}
            selectedIds={selectedIds}
            onToggle={toggleEvent}
          />
          <div className="flex flex-wrap gap-3">
            {preview && preview.matched_count > 0 && (
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting || selectedIds.size === 0}
                className="rounded bg-red-600 px-4 py-2 text-sm text-white disabled:bg-red-300"
              >
                {deleting
                  ? "Deleting…"
                  : selectedIds.size === 0
                    ? "Delete selected"
                    : `Delete ${selectedIds.size} selected`}
              </button>
            )}
            <button
              type="button"
              onClick={() =>
                downloadReportCsv(
                  displayReport,
                  result ? `fbf-purge-${displayReport.course_id}.csv` : `fbf-preview-${displayReport.course_id}.csv`,
                )
              }
              className="rounded border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
            >
              Download CSV
            </button>
          </div>
        </>
      )}

      <p className="text-xs text-slate-400">
        Removes Feedback Fruits calendar entries only—not Canvas assignments or FBF activities.
      </p>
    </div>
  );
}
