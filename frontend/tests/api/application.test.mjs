import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import test from "node:test";

const runId = process.env.VOXNOVA_TEST_RUN_ID;
const port = Number(process.env.VOXNOVA_TEST_API_PORT);
const webPort = Number(process.env.VOXNOVA_TEST_WEB_PORT);
assert.match(runId ?? "", /^[a-z0-9][a-z0-9-]{0,40}$/);
for (const value of [port, webPort]) {
  assert.ok(Number.isInteger(value) && value > 1024 && value < 65536);
  assert.ok(
    ![13080, 13081, 13082].includes(value),
    "Refusing shared POC ports",
  );
}
const base = `http://127.0.0.1:${port}`;
const origin = `http://127.0.0.1:${webPort}`;
function client() {
  let cookie = "";
  return async (path, status, method = "GET", body) => {
    const response = await fetch(base + path, {
      method,
      headers: {
        Origin: origin,
        Cookie: cookie,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    assert.equal(response.status, status, `${method} ${path}`);
    const setCookie = response.headers.getSetCookie()[0];
    if (setCookie) cookie = setCookie.split(";")[0];
    return response.status === 204 ? null : response.json();
  };
}
test("dedicated HTTP application flow: validation, drafts, persistence, conflicts and access boundaries", async () => {
  const request = client();
  const anonymous = client();
  assert.equal((await request("/api/health", 200)).status, "ok");
  await anonymous("/api/applications", 401);
  const email = `issue8-${randomBytes(8).toString("hex")}@example.com`;
  const password = randomBytes(24).toString("base64url");
  for (const invalid of ["", "short", "x".repeat(129)]) {
    const error = await request("/api/auth/register", 422, "POST", {
      email,
      password: invalid,
    });
    assert.ok(error.fields.includes("password"));
  }
  await request("/api/auth/register", 422, "POST", {
    email: "invalid",
    password,
  });
  assert.equal(
    (await request("/api/auth/register", 201, "POST", { email, password }))
      .role,
    "applicant",
  );
  await request("/api/staff/applications", 403);
  const values = {
    name: "Synthetic 合成申请人",
    contact_email: email,
    statement: "Synthetic teaching statement. No personal data.",
  };
  for (const invalid of [
    { name: " " },
    { name: "x".repeat(101) },
    { contact_email: "invalid" },
    { statement: " " },
    { statement: "x".repeat(5001) },
  ]) {
    await request("/api/applications", 422, "POST", { ...values, ...invalid });
  }
  let item = await request("/api/applications", 201, "POST", {
    ...values,
    name: "x".repeat(100),
    statement: "x".repeat(5000),
  });
  assert.equal(item.status, "draft");
  const path = `/api/applications/${item.id}`;
  await request("/api/applications", 409, "POST", values);
  await request(path, 422, "PATCH", { ...values, expected_version: 0 });
  await request(path, 409, "PATCH", {
    ...values,
    expected_version: item.version + 100,
  });
  item = await request(path, 200, "PATCH", {
    ...values,
    expected_version: item.version,
  });
  assert.equal(item.name, values.name);
  assert.equal(item.statement, values.statement);
  assert.equal((await request(path, 200)).statement, values.statement);
  const other = client();
  await other("/api/auth/register", 201, "POST", {
    email: `other-${randomBytes(8).toString("hex")}@example.com`,
    password,
  });
  await other(path, 404);
  await anonymous(path, 401);
  const submitted = await request(`${path}/submit`, 200, "POST", {
    expected_version: item.version,
  });
  assert.equal(submitted.status, "submitted");
  assert.ok(
    submitted.events.some(
      (event) => event.before === "draft" && event.after === "submitted",
    ),
  );
  await request(path, 409, "PATCH", {
    ...values,
    expected_version: submitted.version,
  });
  await request(`${path}/submit`, 409, "POST", {
    expected_version: submitted.version,
  });
  await request("/api/auth/logout", 204, "POST");
  await request(path, 401);
  await request("/api/auth/login", 401, "POST", {
    email,
    password: "wrong-password-long",
  });
  await request("/api/auth/login", 200, "POST", { email, password });
  const restored = await request(path, 200);
  assert.equal(restored.status, "submitted");
  assert.equal(restored.statement, values.statement);
});
