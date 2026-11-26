import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: {
    timeout: 45_000,
  },
  use: {
    baseURL: process.env.E2E_FRONTEND_URL || "http://127.0.0.1:13000",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure",
  },
});
