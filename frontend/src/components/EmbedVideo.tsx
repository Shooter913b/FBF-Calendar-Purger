import { getVideoEmbedSrc } from "@/lib/videoEmbed";

export function EmbedVideo({
  url,
  title = "How-to video",
}: {
  url: string | undefined;
  title?: string;
}) {
  const embedSrc = getVideoEmbedSrc(url);
  if (!embedSrc) return null;

  return (
    <div className="overflow-hidden rounded border border-slate-200 bg-black">
      <div className="relative aspect-video w-full">
        <iframe
          src={embedSrc}
          title={title}
          className="absolute inset-0 h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>
    </div>
  );
}
