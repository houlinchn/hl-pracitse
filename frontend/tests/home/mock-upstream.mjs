import { createServer } from "node:http";
const port = Number(process.env.VOXNOVA_TEST_MOCK_PORT);
if (
  !Number.isInteger(port) ||
  port < 1024 ||
  [13080, 13081, 13082].includes(port)
)
  throw new Error("Dedicated mock port required");
// A closed boundary: never proxies or connects to a real API. Browser fixtures
// handle expected API calls; an unmocked call gets an explicit test failure.
createServer((req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.statusCode = req.url === "/ready" ? 200 : 503;
  res.end(
    JSON.stringify({
      detail: "Isolated homepage mock upstream; no real API fallback",
    }),
  );
}).listen(port, "127.0.0.1");
