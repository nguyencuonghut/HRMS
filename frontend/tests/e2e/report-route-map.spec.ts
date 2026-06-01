import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports)/);
}

test.describe("Report route map", () => {
  test("report hub exposes canonical report links", async ({ page }) => {
    await login(page);
    await page.goto("/reports");
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

    await page.goto("/reports/probation");
    await page.waitForLoadState("networkidle");
    await expect(main.locator(".ob-breadcrumb span").getByText("Báo cáo thử việc")).toBeVisible();

    await page.goto("/reports/leave");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo nghỉ phép" })).toBeVisible();

    await page.goto("/reports/recruitment");
    await page.waitForLoadState("networkidle");
    await expect(main.locator(".rc-jr-code")).toHaveText("Báo cáo tuyển dụng");

    await page.goto("/reports/training");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo đào tạo" })).toBeVisible();

    await page.goto("/reports/rewards");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo khen thưởng & kỷ luật" })).toBeVisible();

    await page.goto("/reports/performance");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo hiệu suất / KPI" })).toBeVisible();
  });
});
