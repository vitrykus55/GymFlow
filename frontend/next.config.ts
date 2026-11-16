import type { NextConfig } from "next";

// Where the FastAPI backend lives. The browser calls /api/v1/* on the same origin
// and Next.js proxies it, so the refresh-token cookie stays first-party.
const backendUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Produces a minimal self-contained server in .next/standalone for the Docker image
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${backendUrl}/api/v1/:path*` }];
  },
};

export default nextConfig;
