import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@patchbay/shared-types"],
};

export default nextConfig;
