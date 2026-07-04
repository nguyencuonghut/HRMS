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

test.describe("Dashboard tổng quan", () => {
  test("renders and loads report data in light mode", async ({ page }) => {
    await login(page);
    await page.goto("/reports/dashboard");

    await expect(
      page.getByRole("heading", { name: "Dashboard tổng quan" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Headcount theo phòng ban/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Biến động 12 tháng/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Cơ cấu nhân sự/i }),
    ).toBeVisible();
    await expect(page.getByText("Trong tỉnh / ngoài tỉnh")).toBeVisible();
    await expect(page.getByText("Loại hợp đồng lao động")).toBeVisible();

    await page.waitForLoadState("networkidle");

    const errorBanner = page.locator(".dashboard-error");
    await expect(errorBanner).toHaveCount(0);

    const kpiCards = page.locator(".dashboard-kpi-card");
    await expect(kpiCards).toHaveCount(4);

    const headcountCards = page.locator(".headcount-card");
    await expect(headcountCards.first()).toBeVisible();
    expect(await headcountCards.count()).toBeGreaterThan(0);

    const lineChart = page.locator(".line-chart-svg");
    await expect(lineChart).toBeVisible();

    const donutCharts = page.locator(".pie-summary-chart");
    await expect(donutCharts).toHaveCount(3);
  });

  test("applies dark mode skin without breaking dashboard layout", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem("hrms-dark-mode", "true");
    });

    await login(page);
    await page.goto("/reports/dashboard");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("html.dark-mode")).toHaveCount(1);
    await expect(page.locator(".dashboard-kpi-card").first()).toBeVisible();
    await expect(page.locator(".dashboard-card").first()).toBeVisible();
    await expect(page.locator(".headcount-card").first()).toBeVisible();

    const cardBg = await page
      .locator(".dashboard-card")
      .first()
      .evaluate((el) => getComputedStyle(el).backgroundColor);
    const kpiBg = await page
      .locator(".dashboard-kpi-card")
      .first()
      .evaluate((el) => getComputedStyle(el).backgroundColor);

    expect(cardBg).not.toBe("rgb(255, 255, 255)");
    expect(kpiBg).not.toBe("rgb(255, 255, 255)");
  });

  test("supports full-year mode from the month filter", async ({ page }) => {
    await login(page);
    await page.goto("/reports/dashboard");
    await page.waitForLoadState("networkidle");

    const monthSelect = page.locator(".dashboard-toolbar .p-select").nth(1);
    await monthSelect.click();
    await page.getByText("Toàn năm", { exact: true }).click();
    await expect(monthSelect).toContainText("Toàn năm");

    const summaryResponse = page.waitForResponse((response) => {
      return (
        response.url().includes("/api/v1/reports/dashboard/summary") &&
        response.request().method() === "GET" &&
        !response.request().url().includes("month=")
      );
    });

    await page.getByRole("button", { name: "Xem báo cáo" }).click();

    const response = await summaryResponse;
    expect(response.request().url()).not.toContain("month=");

    await expect(page.getByRole("heading", { name: /KPI năm \d{4}/ })).toBeVisible();
    await expect(page.locator(".dashboard-kpi-card")).toContainText([
      "Mới trong năm",
      "Nghỉ việc trong năm",
    ]);
  });
});
