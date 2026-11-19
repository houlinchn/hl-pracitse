import { expect, test } from "@playwright/test";
import { randomBytes } from "node:crypto";

test("专属真实全栈：健康、注册、草稿保存、提交与持久化", async ({
  page,
  baseURL,
  playwright,
}, info) => {
  const email = `home-${randomBytes(6).toString("hex")}@example.com`;
  const password = randomBytes(24).toString("base64url");
  const health = await page.request.get("/api/health");
  expect(health.status()).toBe(200);
  expect((await health.json()).status).toBe("ok");
  await page.goto("/");
  await page.getByRole("button", { name: "开始申请" }).click();
  await page.getByLabel("邮箱", { exact: true }).fill(email);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "创建账号并继续" }).click();
  await expect(page.getByRole("heading", { name: "我的申请." })).toBeVisible();
  await page
    .getByLabel("姓名", { exact: false })
    .fill("Voxnova Synthetic Applicant");
  await page.getByLabel("联系邮箱").fill(email);
  await page
    .getByLabel("申请说明")
    .fill("Synthetic isolated homepage acceptance. No personal information.");
  await page.getByRole("button", { name: "保存草稿" }).click();
  await expect(page.getByRole("button", { name: "确认提交" })).toBeEnabled();
  await page.reload();
  await expect(page.getByLabel("姓名", { exact: false })).toHaveValue(
    "Voxnova Synthetic Applicant",
  );
  await page
    .getByLabel("申请说明")
    .fill("Edited synthetic teaching application.");
  await expect(page.getByRole("button", { name: "确认提交" })).toBeDisabled();
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByRole("button", { name: "确认提交" })).toBeEnabled();
  await page.getByRole("button", { name: "确认提交" }).click();
  await expect(page.getByTestId("own-status")).toHaveText("已提交");
  await page.reload();
  await expect(page.getByTestId("own-status")).toHaveText("已提交");
  await expect(
    page.getByText("Edited synthetic teaching application.", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const ownList = await page.request.get("/api/applications");
  const item = (await ownList.json())[0];
  expect(item.status).toBe("submitted");
  const detail = await page.request.get(`/api/applications/${item.id}`);
  expect(detail.status()).toBe(200);
  expect(
    (await detail.json()).events.some(
      (event: { after: string }) => event.after === "submitted",
    ),
  ).toBe(true);
  const forbidden = await page.request.get("/api/staff/applications");
  expect(forbidden.status()).toBe(403);
  const locked = await page.request.patch(`/api/applications/${item.id}`, {
    headers: { Origin: baseURL! },
    data: {
      name: "Cannot edit",
      contact_email: email,
      statement: "Attempt",
      expected_version: item.version,
    },
  });
  expect(locked.status()).toBe(409);
  const anonymous = await playwright.request.newContext({ baseURL });
  expect((await anonymous.get(`/api/applications/${item.id}`)).status()).toBe(
    401,
  );
  await anonymous.dispose();
  await page.screenshot({
    path: info.outputPath("real-submitted.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "退出登录" }).click();
  await page.getByRole("button", { name: "登录工作台" }).click();
  await page.getByLabel("邮箱", { exact: true }).fill(email);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录 →", exact: true }).click();
  await expect(page.getByTestId("own-status")).toHaveText("已提交");
});
