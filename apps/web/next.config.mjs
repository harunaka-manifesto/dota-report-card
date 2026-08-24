/** @type {import('next').NextConfig} */
function apiBaseUrl() {
  const configured = process.env.API_BASE_URL?.trim();
  if (!configured) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("API_BASE_URL must be set for production web builds");
    }
    return "http://localhost:8000";
  }
  let parsed;
  try {
    parsed = new URL(configured);
  } catch {
    throw new Error("API_BASE_URL must be an absolute URL");
  }
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("API_BASE_URL must use http or https");
  }
  if (
    process.env.NODE_ENV === "production" &&
    ["localhost", "127.0.0.1", "::1", "[::1]"].includes(parsed.hostname)
  ) {
    throw new Error("API_BASE_URL must point to the production API");
  }
  return parsed.toString().replace(/\/$/, "");
}

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/v1/:path*", destination: `${apiBaseUrl()}/v1/:path*` }];
  }
};

export default nextConfig;
