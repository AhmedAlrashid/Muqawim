import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactStrictMode: true,
  images: {
    domains: ["liberties.aljazeera.com"],
  },
};

export default nextConfig;
