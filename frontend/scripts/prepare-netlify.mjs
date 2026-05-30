import { mkdirSync, writeFileSync } from "node:fs";

/** Write Netlify _redirects for API proxy and legacy paths (static export has no rewrites). */
const backend = (process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\/$/, "");
const lines = [
  "/courses  /  302",
  "/help  /  302",
  "/purge/:courseId/confirm  /?course=:courseId  302",
  "/purge/:courseId  /?course=:courseId  302",
];

if (backend) {
  lines.unshift(`/api/*  ${backend}/api/:splat  200`);
} else {
  console.warn(
    "NEXT_PUBLIC_BACKEND_URL is not set — /api/* proxy redirect will be missing.",
  );
}

mkdirSync("public", { recursive: true });
writeFileSync("public/_redirects", `${lines.join("\n")}\n`);
console.log("Wrote public/_redirects for Netlify");
