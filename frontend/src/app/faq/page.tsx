import Link from "next/link";
import { EmbedVideo } from "@/components/EmbedVideo";
import { FAQ_VIDEO_URL } from "@/lib/videoEmbed";

export default function FaqPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">FAQ</h1>
        <Link href="/" className="text-sm text-slate-600 underline hover:text-slate-900">
          Back to purger
        </Link>
      </div>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-slate-900">
          What about linked assignments?
        </h2>
        <p className="text-sm text-slate-600">
          When you turn off <strong>orphaned events only</strong>, some calendar entries show as{" "}
          <strong>Linked</strong>. Those are different from orphans.
        </p>
        <ol className="list-decimal space-y-3 pl-5 text-sm text-slate-700">
          <li>
            <strong>What linked assignments are:</strong> The calendar event still points at a
            Canvas assignment that exists. Feedback Fruits is managing that entry, and the date on
            the calendar should match the due date in the corresponding FBF activity.
          </li>
          <li>
            <strong>If you delete a linked event:</strong> You break that connection. Feedback
            Fruits will not automatically recreate the calendar entry, so you need extra steps if
            you want it on the student calendar again.
          </li>
          <li>
            <strong>To get the calendar entry back:</strong> Open the FBF assignment (purple Edit
            button), remove the due dates, click the sync button, wait a minute or two, re-add the
            due dates, and click the sync button again.
          </li>
        </ol>

        <EmbedVideo url={FAQ_VIDEO_URL} title="Relinking FBF calendar events" />
      </section>
    </div>
  );
}
