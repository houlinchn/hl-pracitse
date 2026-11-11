import {
  test,
  expect,
  applicant,
  staff,
  application,
  noOverflow,
} from "./fixtures";

test("首页内容、元信息、导航与响应式截图", async ({ page, scenario }, info) => {
  await scenario();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "让热爱教学的你，被更多可能听见。",
  );
  await expect(page).toHaveTitle("Voxnova · 在线英语教师招聘");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute(
    "content",
    /Voxnova/,
  );
  await expect(page.getByRole("link", { name: "Voxnova 首页" })).toBeVisible();
  await page.getByRole("link", { name: "认识教师岗位" }).click();
  await expect(page).toHaveURL(/#position$/);
  await page
    .locator("summary")
    .filter({ hasText: "资料没写完，可以下次继续吗？" })
    .click();
  await expect(page.locator("details[open]")).toContainText("草稿仅你本人可见");
  await noOverflow(page);
  await page.getByRole("link", { name: "回到顶部" }).click();
  await page.screenshot({
    path: info.outputPath("homepage.png"),
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("申请入口、键盘焦点约束、关闭与焦点恢复", async ({ page, scenario }) => {
  await scenario();
  await page.goto("/");
  const apply = page.getByRole("button", { name: "开始申请", exact: false });
  await apply.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading")).toHaveText("开始你的申请.");
  await expect(page.getByLabel("邮箱", { exact: true })).toBeFocused();
  await dialog.getByRole("button", { name: "关闭登录" }).focus();
  await page.keyboard.press("Shift+Tab");
  await expect(
    dialog.getByRole("button", { name: "创建账号并继续" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(dialog.getByRole("button", { name: "关闭登录" })).toBeFocused();
  const focusStyle = await dialog
    .getByRole("button", { name: "关闭登录" })
    .evaluate((el) => getComputedStyle(el).outlineStyle);
  expect(focusStyle).not.toBe("none");
  await noOverflow(page);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(apply).toBeFocused();
  await page.getByRole("button", { name: "登录工作台" }).click();
  await expect(dialog.getByRole("heading")).toHaveText("欢迎回来.");
  await dialog.getByRole("button", { name: "关闭登录" }).click();
  await expect(page.getByRole("button", { name: "登录工作台" })).toBeFocused();
  await page
    .getByRole("button", { name: "创建申请人账号", exact: false })
    .click();
  await expect(dialog.getByRole("heading")).toHaveText("开始你的申请.");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "已有账号？登录" }).click();
  await expect(dialog.getByRole("heading")).toHaveText("欢迎回来.");
});

test("加载及认证失败状态可读", async ({ page, scenario }) => {
  await scenario({ authFailure: true, slowAuth: true, failMe: 503 });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("服务暂时不可用");
  await page.getByRole("button", { name: "开始申请" }).click();
  await page.getByLabel("邮箱", { exact: true }).fill("synthetic@example.com");
  await page
    .getByLabel("密码", { exact: true })
    .fill("Synthetic-only-password");
  await page.getByRole("button", { name: "创建账号并继续" }).click();
  await expect(page.getByRole("button", { name: "处理中" })).toBeDisabled();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "服务暂时不可用",
  );
  await noOverflow(page);
});

test("申请人布局（模拟资料）", async ({ page, scenario }, info) => {
  await scenario({ account: applicant, applications: [application] });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "我的申请." })).toBeVisible();
  await expect(page.getByTestId("own-status")).toHaveText("已提交");
  await noOverflow(page);
  await page.screenshot({
    path: info.outputPath("applicant-fixture.png"),
    fullPage: true,
  });
});

test("员工详情及委托布局（模拟资料，无令牌）", async ({
  page,
  scenario,
}, info) => {
  await scenario({ account: staff, applications: [application] });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "申请管理." })).toBeVisible();
  await page
    .getByRole("button", { name: `查看 ${application.name} 的申请` })
    .click();
  await expect(page.getByTestId("detail-status")).toHaveText("已提交");
  await noOverflow(page);
  await page.screenshot({
    path: info.outputPath("staff-fixture.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "AI 委托", exact: true }).click();
  await expect(
    page.getByText("synthetic-grant", { exact: true }),
  ).toBeVisible();
  await noOverflow(page);
  await page.screenshot({
    path: info.outputPath("delegations-fixture.png"),
    fullPage: true,
  });
});

for (const status of [401, 503]) {
  test(`工作台列表失败 ${status}（模拟）`, async ({ page, scenario }) => {
    await scenario({ account: staff, failList: status });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "申请管理." }),
    ).toBeVisible();
    await page.getByRole("button", { name: "刷新", exact: true }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await noOverflow(page);
  });
}

test("无查看权限及委托失败（模拟）", async ({ page, scenario }) => {
  await scenario({
    account: { ...staff, permissions: [] },
    failDelegations: 503,
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "暂无查看权限" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "AI 委托", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("委托暂时无法加载");
  await noOverflow(page);
});

test("首次加载状态可读", async ({ page, scenario }) => {
  await scenario({ slowMe: true });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("status")).toHaveText("正在连接工作台…");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});
