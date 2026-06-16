import { formatEventDate } from "@/lib/api";
import type { PurgeEventResult } from "@/types";

function linkStatusLabel(status: PurgeEventResult["link_status"]): string | null {
  if (status === "orphan") return "Orphan";
  if (status === "linked") return "Linked";
  if (status === "unlinked") return "No link";
  if (status === "unknown") return "Unknown link";
  return null;
}

function categoryLabel(category: PurgeEventResult["event_category"]): string {
  return category === "user" ? "User" : "FBF";
}

function isRowSelectable(ev: PurgeEventResult, selectable: boolean): boolean {
  return selectable && ev.calendar_entry_kind !== "assignment_due";
}

function isLinkableUrl(url: string): boolean {
  return (
    url.includes("/calendar") ||
    url.includes("/appointment_groups") ||
    url.includes("/assignments/")
  );
}

export function EventTable({
  events,
  showStatus = false,
  showLinkStatus = false,
  showCategory = false,
  selectable = false,
  selectedIds,
  onToggle,
}: {
  events: PurgeEventResult[];
  showStatus?: boolean;
  showLinkStatus?: boolean;
  showCategory?: boolean;
  selectable?: boolean;
  selectedIds?: Set<number>;
  onToggle?: (eventId: number) => void;
}) {
  const sorted = [...events].sort((a, b) => {
    const ta = a.start_at ? new Date(a.start_at).getTime() : 0;
    const tb = b.start_at ? new Date(b.start_at).getTime() : 0;
    return ta - tb;
  });

  return (
    <div className="overflow-x-auto border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-left">
          <tr>
            {selectable && <th className="w-10 px-3 py-2" aria-label="Select" />}
            <th className="px-3 py-2 font-medium">Date</th>
            {showCategory && <th className="px-3 py-2 font-medium">Type</th>}
            <th className="px-3 py-2 font-medium">Title</th>
            {showLinkStatus && <th className="px-3 py-2 font-medium">Assignment</th>}
            {showStatus && <th className="px-3 py-2 font-medium">Status</th>}
          </tr>
        </thead>
        <tbody>
          {sorted.map((ev) => {
            const isUser = ev.event_category === "user";
            const rowSelectable = isRowSelectable(ev, selectable);
            const selected = rowSelectable && selectedIds?.has(ev.event_id);
            return (
              <tr
                key={ev.event_id}
                onClick={
                  rowSelectable && onToggle
                    ? () => onToggle(ev.event_id)
                    : undefined
                }
                className={`border-b border-slate-100 ${
                  rowSelectable ? "cursor-pointer hover:bg-slate-50" : ""
                } ${selected ? "bg-blue-50" : ""} ${isUser ? "bg-slate-50/50" : ""}`}
              >
                {selectable && (
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selected ?? false}
                      onChange={() => onToggle?.(ev.event_id)}
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Select ${ev.title ?? "event"}`}
                      className="h-4 w-4"
                    />
                  </td>
                )}
                <td className="whitespace-nowrap px-3 py-2">{formatEventDate(ev.start_at)}</td>
                {showCategory && (
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      <span
                        className={`inline-block rounded px-2 py-0.5 text-xs ${
                          isUser
                            ? "bg-slate-200 text-slate-800"
                            : "bg-purple-100 text-purple-900"
                        }`}
                      >
                        {categoryLabel(ev.event_category)}
                      </span>
                    </div>
                  </td>
                )}
                <td className="px-3 py-2">
                  {ev.html_url && isLinkableUrl(ev.html_url) ? (
                    <a
                      href={ev.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-700 underline decoration-blue-700/30 hover:text-blue-900 hover:decoration-blue-900/50"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {ev.title ?? "View in Canvas"}
                    </a>
                  ) : (
                    (ev.title ?? "—")
                  )}
                </td>
                {showLinkStatus && (
                  <td className="px-3 py-2">
                    {linkStatusLabel(ev.link_status) && (
                      <span
                        title={ev.link_reason ?? undefined}
                        className={`inline-block rounded px-2 py-0.5 text-xs ${
                          ev.link_status === "orphan"
                            ? "bg-red-100 text-red-900"
                            : ev.link_status === "linked"
                              ? "bg-green-100 text-green-900"
                              : ev.link_status === "unlinked"
                                ? "bg-yellow-100 text-yellow-900"
                                : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {linkStatusLabel(ev.link_status)}
                      </span>
                    )}
                  </td>
                )}
                {showStatus && (
                  <td className="px-3 py-2 text-slate-600">{ev.status}</td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
