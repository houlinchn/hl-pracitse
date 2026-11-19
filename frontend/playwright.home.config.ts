import { defineConfig } from "@playwright/test";

process.umask(0o077);
function testPort(name: string): number {
  const port = Number(process.env[name]);
  if (
    !Number.isInteger(port) ||
    port < 1024 ||
    port > 65535 ||
    [13080, 13081, 13082].includes(port)
  )
    throw new Error(
      `${name} must explicitly select a dedicated, non-POC loopback port`,
    );
  return port;
}
const webPort = testPort("VOXNOVA_TEST_WEB_PORT");
const mockPort = testPort("VOXNOVA_TEST_MOCK_PORT");
if (webPort === mockPort) throw new Error("Test ports must be distinct");
const origin = `http://127.0.0.1:${webPort}`;
export default defineConfig({
  testDir: "./tests/home",
  testMatch: "**/*.spec.ts",
  outputDir: "./test-results/home",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  retries: 0,
  reporter: "list",
  use: { baseURL: origin, trace: "off", video: "off", screenshot: "off" },
  projects: [1440, 390, 320].map((width) => ({
    name: `${width}`,
    use: { viewport: { width, height: 1000 } },
  })),
  webServer: [
    {
      command: "node tests/home/mock-upstream.mjs",
      url: `http://127.0.0.1:${mockPort}/ready`,
      reuseExistingServer: false,
      env: { VOXNOVA_TEST_MOCK_PORT: String(mockPort) },
    },
    {
      command: "node .output/server/index.mjs",
      url: origin,
      reuseExistingServer: false,
      env: {
        HOST: "127.0.0.1",
        PORT: String(webPort),
        NUXT_API_BASE: `http://127.0.0.1:${mockPort}`,
      },
    },
  ],
});
