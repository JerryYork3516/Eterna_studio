import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  transpilePackages: ["@eterna/shared-schema"],
  // Hide the Next.js dev-tools indicator (bottom-left) so it doesn't clash with
  // the canvas UI. Dev-only, no end-user value here.
  devIndicators: false
};

export default nextConfig;
