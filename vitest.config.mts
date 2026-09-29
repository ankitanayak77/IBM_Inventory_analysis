import { defineConfig } from "vitest/config";
import { config as loadEnv } from "dotenv";

// Vitest/Vite does not automatically load .env.local into process.env for
// Node-side test code (that's a Next.js-specific convention, not a Vite
// default — Vite's own .env loading only exposes VITE_-prefixed vars to
// import.meta.env on the client). Loaded explicitly here so
// src/db/__tests__/repository.test.ts can see DATABASE_URL.
loadEnv({ path: ".env.local" });

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"],
    testTimeout: 20000,
  },
  resolve: {
    // Native tsconfig-paths resolution (Vite >= 8): reads the "@/*" alias
    // directly from tsconfig.json, so Vitest's module resolution can never
    // drift from what tsc/Next.js already resolve. Vite itself recommended
    // this over the vite-tsconfig-paths plugin (which is now redundant).
    tsconfigPaths: true,
  },
});
