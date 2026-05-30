import { formatEventDate } from "@/lib/api";
import type { PurgeEventResult } from "@/types";

export function EventTable({
  events,
  showStatus = false,
  selectable = false,
  selectedIds,
  onToggle,
}: {
  events: PurgeEventResult[];
  showStatus?: boolean;
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
            <th className="px-3 py-2 font-medium">Title</th>
            {showStatus && <th className="px-3 py-2 font-medium">Status</th>}
          </tr>
        </thead>
        <tbody>
          {sorted.map((ev) => {
            const selected = selectable && selectedIds?.has(ev.event_id);
            return (
              <tr
                key={ev.event_id}
                onClick={
                  selectable && onToggle
                    ? () => onToggle(ev.event_id)
                    : undefined
                }
                className={`border-b border-slate-100 ${
                  selectable ? "cursor-pointer hover:bg-slate-50" : ""
                } ${selected ? "bg-blue-50" : ""}`}
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
                <td className="px-3 py-2">{ev.title ?? "—"}</td>
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
