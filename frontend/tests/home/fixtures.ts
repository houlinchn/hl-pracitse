import { test as base, expect, type Page } from "@playwright/test";
import type { Account, Application } from "../../composables/usePortal";

export const applicant: Account = {
  id: "synthetic-applicant",
  email: "applicant@example.com",
  role: "applicant",
  permissions: [],
};
export const staff: Account = {
  id: "synthetic-staff",
  email: "staff@example.com",
  role: "staff",
  permissions: ["applications.read", "applications.advance", "audit.read"],
};
export const application: Application = {
  id: "synthetic-application",
  applicant_id: applicant.id,
  name: "Alex Example",
  contact_email: applicant.email,
  statement: "Synthetic teaching experience. No personal information.",
  status: "submitted",
  version: 2,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
  events: [],
};

type Scenario = {
  account?: Account;
  applications?: Application[];
  failList?: number;
  failMe?: number;
  failDelegations?: number;
  authFailure?: boolean;
  slowAuth?: boolean;
  slowMe?: boolean;
};
export const test = base.extend<{
  scenario: (data?: Scenario) => Promise<void>;
}>({
  scenario: async ({ page, baseURL }, use) => {
    const unexpected: string[] = [];
    await use(async (data = {}) => {
      await page.route("**/*", async (route) => {
        const request = route.request();
        const url = new URL(request.url());
        if (url.origin !== baseURL) {
          unexpected.push("external request");
          await route.abort();
          return;
        }
        if (!url.pathname.startsWith("/api/")) {
          await route.continue();
          return;
        }
        const path = url.pathname;
        let status = 200;
        let body: unknown;
        if (path === "/api/auth/me") {
          if (data.slowMe)
            await new Promise((resolve) => setTimeout(resolve, 1500));
          status = data.failMe || (data.account ? 200 : 401);
          body = data.account || { detail: "请登录" };
          if (data.failMe) body = { detail: "服务暂时不可用，请稍后重试" };
        } else if (
          path === "/api/auth/login" ||
          path === "/api/auth/register"
        ) {
          if (data.slowAuth)
            await new Promise((resolve) => setTimeout(resolve, 700));
          status = data.authFailure ? 503 : 200;
          body = data.authFailure
            ? { detail: "服务暂时不可用，请稍后重试" }
            : applicant;
        } else if (
          path === "/api/applications" ||
          path === "/api/staff/applications"
        ) {
          status = data.failList || 200;
          body = data.failList
            ? {
                detail:
                  data.failList === 401
                    ? "登录已过期，请重新登录"
                    : "申请暂时无法加载，请稍后重试",
              }
            : data.applications || [];
        } else if (path.endsWith(`/${application.id}`)) {
          body = (data.applications || [application])[0];
        } else if (path === "/api/delegations") {
          status = data.failDelegations || 200;
          body = data.failDelegations
            ? { detail: "委托暂时无法加载，请稍后重试" }
            : [
                {
                  id: "synthetic-grant",
                  permissions: ["applications.read"],
                  application_ids: null,
                  expires_at: "2099-01-01T12:00:00Z",
                  revoked: false,
                  expired: false,
                },
              ];
        } else {
          unexpected.push(`${request.method()} ${path}`);
          status = 500;
          body = { detail: "Unexpected mock request" };
        }
        await route.fulfill({ status, json: body });
      });
    });
    expect(
      unexpected,
      "Every API call must be explicitly mocked; external calls are blocked",
    ).toEqual([]);
  },
});
export { expect };
export async function noOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
}
