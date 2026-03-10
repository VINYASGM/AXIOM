import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  typescript: {
    ignoreBuildErrors: false,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8080/api/:path*', // Proxy to Go Backend
      },
    ];
  },
};

export default nextConfig;
