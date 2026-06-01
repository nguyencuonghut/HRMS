import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);

  const loginMeResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await loginMeResponse;
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports)/);
}

async function navigate(page: Page, path: string) {
  await page.evaluate((nextPath) => {
    window.history.pushState({}, "", nextPath);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
}

test.describe.configure({ mode: "serial" });

test.describe("Report route map", () => {
  test("report hub exposes canonical report links", async ({ page }) => {
    await login(page);
    await navigate(page, "/reports");
    await page.waitForLoadState("networkidle");

    const main = page.locator("#main-content");
    await expect(main.getByRole("heading", { name: "Báo cáo", exact: true })).toBeVisible();
    await expect(main.getByRole("link", { name: /Dashboard tổng quan/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo thử việc/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo tuyển dụng/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo đào tạo/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo hiệu suất/i })).toBeVisible();
  });

  test("new canonical report routes render", async ({ page }) => {
    await login(page);
    const main = page.locator("#main-content");

    await navigate(page, "/reports/probation");
    await page.waitForLoadState("networkidle");
    await expect(main.locator(".ob-breadcrumb span").getByText("Báo cáo thử việc")).toBeVisible();

    await navigate(page, "/reports/leave");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo nghỉ phép" })).toBeVisible();

    await navigate(page, "/reports/recruitment");
    await page.waitForLoadState("networkidle");
    await expect(main.locator(".rc-jr-code")).toHaveText("Báo cáo tuyển dụng");

    await navigate(page, "/reports/training");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo đào tạo" })).toBeVisible();

    await navigate(page, "/reports/rewards");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo khen thưởng & kỷ luật" })).toBeVisible();

    await navigate(page, "/reports/performance");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo hiệu suất / KPI" })).toBeVisible();
  });

  test("legacy report routes redirect to canonical routes", async ({ page }) => {
    await login(page);

    await navigate(page, "/employees/probation-reports");
    await page.waitForURL("**/reports/probation");

    await navigate(page, "/leave-reports");
    await page.waitForURL("**/reports/leave");

    await navigate(page, "/recruitment/reports");
    await page.waitForURL("**/reports/recruitment");
  });
});
