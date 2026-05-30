/** Convert a watch/share URL or embed URL into an iframe src. Returns null if unset or unrecognized. */
export function getVideoEmbedSrc(url: string | undefined): string | null {
  const trimmed = url?.trim();
  if (!trimmed) return null;

  try {
    const parsed = new URL(trimmed);

    if (parsed.hostname.includes("youtube.com")) {
      if (parsed.pathname.startsWith("/embed/")) {
        return trimmed;
      }
      const videoId = parsed.searchParams.get("v");
      if (videoId) {
        return `https://www.youtube.com/embed/${videoId}`;
      }
    }

    if (parsed.hostname === "youtu.be") {
      const videoId = parsed.pathname.replace(/^\//, "");
      if (videoId) {
        return `https://www.youtube.com/embed/${videoId}`;
      }
    }

    if (parsed.hostname.includes("vimeo.com")) {
      if (parsed.hostname === "player.vimeo.com") {
        return trimmed;
      }
      const match = parsed.pathname.match(/\/(\d+)/);
      if (match?.[1]) {
        return `https://player.vimeo.com/video/${match[1]}`;
      }
    }
  } catch {
    return null;
  }

  return null;
}

export const SIGN_IN_VIDEO_URL = process.env.NEXT_PUBLIC_SIGN_IN_VIDEO_URL;
export const MAIN_VIDEO_URL = process.env.NEXT_PUBLIC_MAIN_VIDEO_URL;
