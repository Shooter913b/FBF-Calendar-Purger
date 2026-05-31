/** Convert a watch/share URL or embed URL into an iframe src. Returns null if unset or unrecognized. */
export function getVideoEmbedSrc(url: string | undefined): string | null {
  const trimmed = url?.trim();
  if (!trimmed) return null;

  try {
    const parsed = new URL(trimmed);

    if (parsed.hostname.includes("youtube.com")) {
      if (parsed.pathname.startsWith("/embed/")) {
        return normalizeYouTubeEmbedUrl(parsed);
      }
      const videoId = parsed.searchParams.get("v");
      if (videoId) {
        return buildYouTubeEmbedUrl(videoId, parsed);
      }
    }

    if (parsed.hostname === "youtu.be") {
      const videoId = parsed.pathname.replace(/^\//, "").split("/")[0];
      if (videoId) {
        return buildYouTubeEmbedUrl(videoId, parsed);
      }
    }

    if (parsed.hostname.includes("vimeo.com")) {
      if (parsed.hostname === "player.vimeo.com") {
        return normalizeVimeoEmbedUrl(parsed);
      }
      const match = parsed.pathname.match(/\/(\d+)/);
      if (match?.[1]) {
        return buildVimeoEmbedUrl(match[1], parsed);
      }
    }
  } catch {
    return null;
  }

  return null;
}

function parseYouTubeStartSeconds(parsed: URL): number | null {
  const raw =
    parsed.searchParams.get("start") ??
    parsed.searchParams.get("t") ??
    parsed.hash.match(/[#&]t=([^&]+)/)?.[1];
  if (!raw) return null;
  return youtubeTimeToSeconds(raw);
}

/** Supports 90, 90s, 1m30s, 1h2m30s (YouTube watch-link formats). */
export function youtubeTimeToSeconds(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;

  if (/^\d+$/.test(trimmed)) {
    return Number.parseInt(trimmed, 10);
  }

  const secondsOnly = trimmed.match(/^(\d+)s$/i);
  if (secondsOnly) {
    return Number.parseInt(secondsOnly[1], 10);
  }

  const hours = trimmed.match(/(\d+)h/i);
  const minutes = trimmed.match(/(\d+)m/i);
  const seconds = trimmed.match(/(\d+)s/i);
  if (hours || minutes || seconds) {
    let total = 0;
    if (hours) total += Number.parseInt(hours[1], 10) * 3600;
    if (minutes) total += Number.parseInt(minutes[1], 10) * 60;
    if (seconds) total += Number.parseInt(seconds[1], 10);
    return total;
  }

  return null;
}

function buildYouTubeEmbedUrl(videoId: string, source: URL): string {
  const start = parseYouTubeStartSeconds(source);
  if (start != null && start > 0) {
    return `https://www.youtube.com/embed/${videoId}?start=${start}`;
  }
  return `https://www.youtube.com/embed/${videoId}`;
}

function normalizeYouTubeEmbedUrl(parsed: URL): string {
  const videoId = parsed.pathname.replace(/^\/embed\//, "").split("/")[0];
  if (!videoId) return parsed.toString();

  const start = parseYouTubeStartSeconds(parsed);
  if (start != null && start > 0) {
    return `https://www.youtube.com/embed/${videoId}?start=${start}`;
  }
  return `https://www.youtube.com/embed/${videoId}`;
}

function parseVimeoTimestamp(parsed: URL): string | null {
  if (parsed.hash.startsWith("#t=")) {
    return parsed.hash.slice(1);
  }
  const fromQuery = parsed.searchParams.get("t");
  if (fromQuery) {
    return fromQuery.startsWith("t=") ? fromQuery : `t=${fromQuery}`;
  }
  return null;
}

function buildVimeoEmbedUrl(videoId: string, source: URL): string {
  const timestamp = parseVimeoTimestamp(source);
  const base = `https://player.vimeo.com/video/${videoId}`;
  return timestamp ? `${base}#${timestamp}` : base;
}

function normalizeVimeoEmbedUrl(parsed: URL): string {
  const timestamp = parseVimeoTimestamp(parsed);
  if (!timestamp) return parsed.toString();

  const withoutHash = `${parsed.origin}${parsed.pathname}${parsed.search}`;
  if (parsed.hash === `#${timestamp}`) {
    return parsed.toString();
  }
  return `${withoutHash}#${timestamp}`;
}

export const SIGN_IN_VIDEO_URL = process.env.NEXT_PUBLIC_SIGN_IN_VIDEO_URL;
export const MAIN_VIDEO_URL = process.env.NEXT_PUBLIC_MAIN_VIDEO_URL;
export const FAQ_VIDEO_URL = process.env.NEXT_PUBLIC_FAQ_VIDEO_URL;
