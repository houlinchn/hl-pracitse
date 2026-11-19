import { defineConfig, devices } from "@playwright/test";
process.umask(0o077);
export default defineConfig({
  testDir: "./tests",
  testMatch: "recruitment.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:13080",
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1050 },
      },
    },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
