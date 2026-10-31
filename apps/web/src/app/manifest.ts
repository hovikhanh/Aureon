import type { MetadataRoute } from "next";

/**
 * PWA manifest (SCR-28, R-DEC-25 M2.3): installable mobile shell for the 4 core mobile jobs
 * (capture, voice note, meetings, tasks). Colors track the design tokens (primary blue /
 * near-white background). Icons: no 192/512 PNGs ship yet — reference the existing favicon so the
 * manifest validates; add real maskable icons as a follow-up (noted as a gap).
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Aureon",
    short_name: "Aureon",
    description: "Aureon — AI-EOS: thu thập, hỏi dữ liệu và giao việc trên di động.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#fcfcfc",
    theme_color: "#2b57d6",
    lang: "vi",
    icons: [
      { src: "/favicon.ico", sizes: "48x48", type: "image/x-icon" },
    ],
  };
}
