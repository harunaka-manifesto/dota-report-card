/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
    return [{ source: "/v1/:path*", destination: `${apiBaseUrl}/v1/:path*` }];
  }
};

export default nextConfig;
