import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);
}

test.describe("Phân tích bảo hiểm", () => {
  test("supports full-year mode from the month filter", async ({ page }) => {
    await login(page);
    await page.goto("/reports/insurance");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: "Phân tích bảo hiểm" }),
    ).toBeVisible();

    const monthSelect = page.locator(".toolbar .p-select").nth(1);
    await monthSelect.click();
    await page.getByText("Toàn năm", { exact: true }).click();
    await expect(monthSelect).toContainText("Toàn năm");

    const dashboardResponse = page.waitForResponse((response) => {
      return (
        response.url().includes("/api/v1/reports/insurance/dashboard") &&
        response.request().method() === "GET" &&
        !response.request().url().includes("month=")
      );
    });
    const breakdownResponse = page.waitForResponse((response) => {
      return (
        response.url().includes("/api/v1/reports/insurance/by-department") &&
        response.request().method() === "GET" &&
        !response.request().url().includes("month=")
      );
    });

    await page.getByRole("button", { name: "Lọc" }).click();

    const [dashboard, breakdown] = await Promise.all([
      dashboardResponse,
      breakdownResponse,
    ]);
    expect(dashboard.request().url()).not.toContain("month=");
    expect(breakdown.request().url()).not.toContain("month=");

    await expect(page.locator(".subtitle")).toContainText("toàn năm");
    await expect(page.locator(".kpi-card.border-red")).toContainText("Biến động năm");
  });
});
