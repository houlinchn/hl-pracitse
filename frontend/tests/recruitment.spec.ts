import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { randomBytes } from "node:crypto";

const staffPassword = readFileSync(
  process.env.POC_STAFF_PASSWORD_FILE || "../.local/staff-password",
  "utf8",
).trim();
const origin = "http://127.0.0.1:13080";

test("页面闭环、持久化、员工审核、AI 对等与撤销", async ({
  page,
  context,
}, testInfo) => {
  const suffix = randomBytes(6).toString("hex");
  const name = `Alex Demo ${suffix}`;
  const email = `browser-${suffix}@example.com`;
  const password = randomBytes(24).toString("base64url");
  const consoleErrors: string[] = [];
  page.on("pageerror", (error) => consoleErrors.push(error.name));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /让热爱教学的你/ })).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("landing.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "开始申请" }).click();
  await page.getByLabel("邮箱", { exact: true }).fill(email);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "创建账号并继续" }).click();
  await expect(page.getByRole("heading", { name: "我的申请." })).toBeVisible();
  await page.getByLabel("姓名", { exact: false }).fill(name);
  await page.getByLabel("联系邮箱").fill("invalid-email");
  await page
    .getByLabel("申请说明")
    .fill("Browser QA sample teaching application.");
  await page.getByRole("button", { name: "保存草稿" }).click();
  expect(
    await page
      .getByLabel("联系邮箱")
      .evaluate((el: HTMLInputElement) => el.validity.valid),
  ).toBe(false);
  await page.getByLabel("联系邮箱").fill(email);
  await page.getByRole("button", { name: "保存草稿" }).click();
  await expect(page.getByRole("button", { name: "确认提交" })).toBeVisible();
  await page
    .getByLabel("申请说明")
    .fill("Edited demo statement. No real personal data.");
  await expect(page.getByRole("button", { name: "确认提交" })).toBeDisabled();
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByRole("button", { name: "确认提交" })).toBeEnabled();
  await page.getByRole("button", { name: "确认提交" }).click();
  await expect(page.getByTestId("own-status")).toHaveText("已提交");
  await page.reload();
  await expect(page.getByTestId("own-status")).toHaveText("已提交");
  await expect(
    page.getByText("Edited demo statement. No real personal data.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("applicant-submitted.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "退出登录" }).click();
  await page.getByRole("button", { name: "登录工作台" }).click();
  await page.getByLabel("邮箱", { exact: true }).fill(email);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录 →", exact: true }).click();
  await expect(page.getByTestId("own-status")).toHaveText("已提交");
  await page.getByRole("button", { name: "退出登录" }).click();
  await page.getByRole("button", { name: "登录工作台" }).click();
  await page.getByLabel("邮箱", { exact: true }).fill("staff@example.com");
  await page.getByLabel("密码", { exact: true }).fill(staffPassword);
  await page.getByRole("button", { name: "登录 →", exact: true }).click();
  await expect(page.getByRole("heading", { name: "申请管理." })).toBeVisible();
  await page.getByRole("button", { name: "已提交", exact: true }).click();
  await page
    .getByRole("button", { name: `查看 ${name} 的申请`, exact: true })
    .click();
  await expect(page.getByRole("button", { name: "推进至初筛" })).toBeDisabled();
  await page
    .getByLabel("初筛推进原因")
    .fill("Browser QA: sample reviewed by staff.");
  await page.getByRole("button", { name: "推进至初筛" }).click();
  await expect(page.getByTestId("detail-status")).toHaveText("初筛");
  await page.getByRole("button", { name: "查看此申请审计记录" }).click();
  await expect(page.getByLabel("审计记录")).toContainText("application.status");
  await page.screenshot({
    path: testInfo.outputPath("staff-screening.png"),
    fullPage: true,
  });
  // A second independent applicant tests the AI transition and shared state over real HTTP.
  const other = await context.browser()!.newContext();
  const registration = await other.request.post(`${origin}/api/auth/register`, {
    headers: { Origin: origin },
    data: { email: `ai-${suffix}@example.com`, password },
  });
  expect(registration.status()).toBe(201);
  const created = await other.request.post(`${origin}/api/applications`, {
    headers: { Origin: origin },
    data: {
      name: `AI Demo ${suffix}`,
      contact_email: `ai-${suffix}@example.com`,
      statement: "AI QA demonstration only.",
    },
  });
  expect(created.status()).toBe(201);
  const item = await created.json();
  const submitted = await other.request.post(
    `${origin}/api/applications/${item.id}/submit`,
    { headers: { Origin: origin }, data: { expected_version: 1 } },
  );
  expect(submitted.status()).toBe(200);
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await page
    .getByRole("button", { name: `查看 AI Demo ${suffix} 的申请`, exact: true })
    .click();
  await page.getByRole("button", { name: "AI 委托", exact: true }).click();
  const grantResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/delegations") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "生成委托令牌" }).click();
  const grantId = (await (await grantResponse).json()).id as string;
  await expect(page.getByLabel("AI 委托令牌 · 请妥善保存")).toBeVisible();
  const token = await page.getByLabel("AI 委托令牌 · 请妥善保存").inputValue();
  const headers = { Authorization: `Bearer ${token}` };
  const aiDetail = await page.request.get(`/api/ai/applications/${item.id}`, {
    headers,
  });
  const webDetail = await page.request.get(
    `/api/staff/applications/${item.id}`,
  );
  expect(aiDetail.status()).toBe(200);
  expect(await aiDetail.json()).toEqual(await webDetail.json());
  const aiAdvance = await page.request.post(
    `/api/ai/applications/${item.id}/advance`,
    {
      headers,
      data: {
        expected_version: 2,
        reason: "AI browser QA delegated screening.",
      },
    },
  );
  expect(aiAdvance.status()).toBe(200);
  const aiAudit = await page.request.get(
    `/api/ai/applications/${item.id}/audit`,
    { headers },
  );
  expect(aiAudit.status()).toBe(200);
  const rows = (await aiAudit.json()) as {
    channel: string;
    delegated_by: string | null;
    action: string;
  }[];
  expect(
    rows.some(
      (row) =>
        row.channel === "ai" &&
        row.delegated_by &&
        row.action === "application.status",
    ),
  ).toBe(true);
  // Revoke the newly issued grant through the real employee interface.
  const grantRow = page.locator(".grant").filter({ hasText: grantId });
  await grantRow.getByRole("button", { name: "撤销", exact: true }).click();
  await expect(grantRow.getByText("已撤销", { exact: true })).toBeVisible();
  const invalid = await page.request.get(`/api/ai/applications/${item.id}`, {
    headers,
  });
  expect(invalid.status()).toBe(401);
  await page.getByRole("button", { name: "申请管理", exact: false }).click();
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page.getByTestId("detail-status")).toHaveText("初筛");
  await expect(
    page.getByText("AI browser QA delegated screening.", { exact: true }),
  ).toBeVisible();
  const ownerView = await other.request.get(
    `${origin}/api/applications/${item.id}`,
  );
  expect((await ownerView.json()).status).toBe("screening");
  await page.screenshot({
    path: testInfo.outputPath("ai-screening.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(consoleErrors).toEqual([]);
  await other.close();
});
