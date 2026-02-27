import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: process.env.NEXT_PUBLIC_BASE_PATH,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:3900/api/:path*",
      },
    ];
  },
};

export default nextConfig;
