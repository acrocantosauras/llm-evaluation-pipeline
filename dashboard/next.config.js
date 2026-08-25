/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // NOTE: /api/* is intentionally NOT rewritten here. It is handled by the
    // server-side proxy route (src/app/api/[...path]/route.ts) which injects the
    // API key. Rewrites cannot add a secret auth header, so they must not be used
    // for authenticated endpoints.
    //
    // /health is public (no auth) and is proxied transparently so the browser
    // only ever talks to the same origin.
    const apiUrl =
      process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/health",
        destination: `${apiUrl}/health`,
      },
    ];
  },
};

module.exports = nextConfig;
