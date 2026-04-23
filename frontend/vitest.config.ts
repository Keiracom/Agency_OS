/**
 * FILE: frontend/vitest.config.ts
 * PURPOSE: Vitest configuration — jsdom env, path aliases matching tsconfig.json
 * PHASE: PHASE-2.1-REALTIME-VITEST
 */
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@":            path.resolve(__dirname, "."),
      "@/components": path.resolve(__dirname, "components"),
      "@/lib":        path.resolve(__dirname, "lib"),
      "@/hooks":      path.resolve(__dirname, "hooks"),
      "@/types":      path.resolve(__dirname, "types"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["lib/**/__tests__/**/*.test.{ts,tsx}", "components/**/__tests__/**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next", "design/**"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
