import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/**
 * Dev proxy: browser calls to `/api/v1/*` are rewritten to the FastAPI backend
 * so same-origin fetch works without CORS. The backend base URL comes from
 * API_BASE_URL (server env), defaulting to the local dev backend.
 * In production, deploy behind a reverse proxy that maps /api/v1 → backend.
 */
const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:4000/api/v1";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@aureon/shared-types"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_BASE_URL}/:path*`,
      },
    ];
  },
};

export default withNextIntl(nextConfig);
