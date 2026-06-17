"use client";

import { FormEvent, useEffect, useState } from "react";
import { EmbedVideo } from "@/components/EmbedVideo";
import { FaqLink } from "@/components/FaqLink";
import {
  type AuthConfig,
  formatApiError,
  getLoginUrl,
  loginWithAccessToken,
  recordVisit,
} from "@/lib/api";
import { SIGN_IN_VIDEO_URL } from "@/lib/videoEmbed";

export function SignInPanel({
  authConfig,
  authError,
  backendUp,
  onSignedIn,
}: {
  authConfig: AuthConfig | null;
  authError: string | null;
  backendUp: boolean | null;
  onSignedIn: () => void;
}) {
  const [token, setToken] = useState("");
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [tokenLoading, setTokenLoading] = useState(false);
  const [lifetimeVisits, setLifetimeVisits] = useState<number | null>(null);

  useEffect(() => {
    recordVisit()
      .then((stats) => setLifetimeVisits(stats.lifetime_visits))
      .catch(() => {
        // Ignore — stats are optional when the backend is down.
      });
  }, []);

  const handleTokenSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) return;
    setTokenLoading(true);
    setTokenError(null);
    try {
      await loginWithAccessToken(trimmed);
      setToken("");
      onSignedIn();
    } catch (err) {
      setTokenError(formatApiError(err));
    } finally {
      setTokenLoading(false);
    }
  };

  const canvasUrl = authConfig?.canvas_base_url ?? "your Canvas site";

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">FBF Calendar Purger</h1>
      <p className="text-sm text-slate-600">
        Sign in to clean up stale Feedback Fruits calendar events in your courses.
      </p>

      {authError && (
        <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {authError}
        </p>
      )}

      {backendUp === false && (
        <p className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Backend is not running. From the <code className="text-xs">backend/</code> folder run:{" "}
          <code className="text-xs">uvicorn api.main:app --reload --port 8000</code>
        </p>
      )}

      <EmbedVideo url={SIGN_IN_VIDEO_URL} title="How to sign in" />

      <div className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold">Sign in with access token</h2>
        <p className="mt-1 text-xs text-slate-600">
          In {canvasUrl}: <strong>Account → Settings → Approved Integrations → New Access Token</strong>.
          Paste the token below. It is stored in your browser session only—not saved on the server.
        </p>
        <form onSubmit={handleTokenSubmit} className="mt-3 space-y-2">
          <label className="block text-xs font-medium text-slate-700">
            Canvas access token
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste token here"
              autoComplete="off"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm font-mono"
            />
          </label>
          {tokenError && (
            <p className="text-sm text-red-700">{tokenError}</p>
          )}
          <button
            type="submit"
            disabled={tokenLoading || !token.trim()}
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:bg-slate-400"
          >
            {tokenLoading ? "Signing in…" : "Sign in with token"}
          </button>
        </form>
      </div>

      {lifetimeVisits !== null && (
        <p className="text-xs text-slate-500">
          {lifetimeVisits.toLocaleString()} lifetime {lifetimeVisits === 1 ? "visit" : "visits"}
        </p>
      )}

      {authConfig?.oauth_enabled && (
        <div className="rounded border border-slate-200 p-4">
          <h2 className="text-sm font-semibold">Or sign in with Canvas OAuth</h2>
          <p className="mt-1 text-xs text-slate-600">Uses your institution&apos;s OAuth — no token to copy.</p>
          <a
            href={getLoginUrl()}
            className="mt-2 inline-block rounded border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50"
          >
            Sign in with Canvas
          </a>
        </div>
      )}

      <FaqLink />
    </div>
  );
}
