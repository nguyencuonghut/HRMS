import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports\/contracts)/);
}

test.describe("Báo cáo hợp đồng", () => {
  test("renders summary, expiring table, charts, history and export", async ({ page }) => {
    await login(page);
    await page.goto("/reports/contracts");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: "Báo cáo hợp đồng" }),
    ).toBeVisible();

    await expect(page.locator(".contract-kpi-card")).toHaveCount(5);
    await expect(page.locator(".contract-expiring-card table")).toBeVisible();
    await expect(page.locator(".contract-donut-chart")).toBeVisible();
    await expect(page.locator(".contract-forecast-row").first()).toBeVisible();

    const autoComplete = page.getByPlaceholder("Nhập mã hoặc tên nhân viên");
    await autoComplete.fill("An");
    await page.waitForTimeout(500);
    const firstOption = page.locator(".contract-employee-option").first();
    await expect(firstOption).toBeVisible();
    await firstOption.click();
    await page.waitForLoadState("networkidle");
    await expect(page.locator(".contract-history-card table")).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Xuất Excel" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  });

  test("opens mobile filter drawer on 375px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 900 });
    await login(page);
    await page.goto("/reports/contracts");
    await page.waitForLoadState("networkidle");

    const filterButton = page.getByRole("button", { name: "Bộ lọc" });
    await expect(filterButton).toBeVisible();
    await filterButton.click();

    const drawer = page.getByRole("dialog");
    await expect(drawer.getByText("Bộ lọc báo cáo hợp đồng")).toBeVisible();
    await expect(drawer.getByText("Cửa sổ sắp hết hạn")).toBeVisible();
    await drawer.getByRole("button", { name: "Áp dụng" }).click();
    await expect(page.getByText("Bộ lọc báo cáo hợp đồng")).toHaveCount(0);
  });
});
