import type { NextConfig } from "next";

const backendUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Standalone is for Docker only; Netlify uses @netlify/plugin-nextjs instead.
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" as const } : {}),
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
