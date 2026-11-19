import { defineConfig } from "@playwright/test";
process.umask(0o077);
const ports = ["VOXNOVA_TEST_WEB_PORT", "VOXNOVA_TEST_API_PORT"].map((name) => {
  const port = Number(process.env[name]);
  if (
    !Number.isInteger(port) ||
    port < 1024 ||
    port > 65535 ||
    [13080, 13081, 13082].includes(port)
  )
    throw new Error(`Dedicated ${name} required`);
  return port;
});
if (ports[0] === ports[1]) throw new Error("Test ports must be distinct");
const origin = `http://127.0.0.1:${ports[0]}`;
export default defineConfig({
  testDir: "./tests/home-fullstack",
  testMatch: "**/*.spec.ts",
  outputDir: "./test-results/home-fullstack",
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: "list",
  use: {
    baseURL: origin,
    viewport: { width: 390, height: 1000 },
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  webServer: {
    command: "node .output/server/index.mjs",
    url: origin,
    reuseExistingServer: false,
    env: {
      HOST: "127.0.0.1",
      PORT: String(ports[0]),
      NUXT_API_BASE: `http://127.0.0.1:${ports[1]}`,
    },
  },
});
