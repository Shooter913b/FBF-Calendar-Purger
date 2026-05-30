const SUPPORT_EMAIL = "ignanasusair@wisc.edu";

export function ScanSlowNotice({
  open,
  onDismiss,
}: {
  open: boolean;
  onDismiss: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="scan-slow-title"
    >
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-5 shadow-lg">
        <h2 id="scan-slow-title" className="text-base font-semibold text-slate-900">
          Still scanning…
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          This can take a minute or two, especially if the server was idle and needs to wake up,
          or if your course has many calendar events. Please keep this tab open—the scan is still
          running.
        </p>
        <p className="mt-3 text-sm text-slate-600">
          If it fails or keeps loading for several minutes, email{" "}
          <a
            href={`mailto:${SUPPORT_EMAIL}`}
            className="font-medium text-slate-900 underline hover:text-slate-700"
          >
            {SUPPORT_EMAIL}
          </a>
          .
        </p>
        <button
          type="button"
          onClick={onDismiss}
          className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
        >
          OK, I&apos;ll wait
        </button>
      </div>
    </div>
  );
}
