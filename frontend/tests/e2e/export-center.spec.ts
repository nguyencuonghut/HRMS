import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports\/export)/);
}

test.describe("Trung tâm xuất báo cáo", () => {
  test("renders quick export, creates job, history and template flows", async ({ page }) => {
    await login(page);
    await page.goto("/reports/export");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: "Xuất báo cáo" }),
    ).toBeVisible();

    const filenameInput = page.getByPlaceholder("Để trống để dùng tên mặc định");
    await filenameInput.fill("playwright_export_center");

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Xuất báo cáo" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/);

    await page.getByRole("tab", { name: "Lịch sử" }).click();
    await page.waitForLoadState("networkidle");
    const historyCard = page.locator(".export-history-card");
    await expect(historyCard.locator("table")).toBeVisible();
    await expect(historyCard.getByText("playwright_export_center", { exact: false }).first()).toBeVisible();

    await page.getByRole("tab", { name: "Xuất nhanh" }).click();
    await page.getByRole("button", { name: "Lưu thành mẫu" }).click();
    await page.getByRole("dialog").getByLabel("Tên mẫu").fill("Playwright Template");
    await page.getByRole("button", { name: "Lưu mẫu" }).click();

    await page.getByRole("tab", { name: "Mẫu" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.locator(".export-template-card table")).toBeVisible();
    await expect(page.getByText("Playwright Template")).toBeVisible();
  });
});
