import type { NextConfig } from "next";

const nextConfig: NextConfig = {
<<<<<<< HEAD
  output: process.env.STANDALONE === "true" ? "standalone" : undefined,
=======
  output: "standalone",
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
};

export default nextConfig;
