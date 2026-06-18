import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";
const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";
const FINANCE_EMAIL = process.env.E2E_FINANCE_EMAIL || "finance@hrms.local";
const FINANCE_PASSWORD = process.env.E2E_FINANCE_PASSWORD || "Hrms@2026";

async function login(page: Page, email: string, password: string, redirect = "/reports/dashboard") {
  await page.goto(`/login?redirect=${encodeURIComponent(redirect)}`);
  await page.getByLabel("Email").fill(email);
  await page.getByPlaceholder("Nhập mật khẩu").fill(password);

  const loginMeResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await loginMeResponse;
  await page.waitForLoadState("networkidle");
}

test.describe("Permission action visibility", () => {
  test("line manager can view org pages but does not see mutate actions", async ({ page }) => {
    await login(page, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD, "/org/job-titles");

    await expect(page).toHaveURL(/\/org\/job-titles$/);
    await expect(page.getByRole("button", { name: "Thêm chức danh" })).toHaveCount(0);
    await expect(page.locator('.pi-pencil')).toHaveCount(0);
    await expect(page.locator('.pi-trash')).toHaveCount(0);

    await page.goto("/org/positions");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: "Thêm vị trí mới" })).toHaveCount(0);
    await expect(page.locator('.pi-pencil')).toHaveCount(0);
    await expect(page.locator('.pi-trash')).toHaveCount(0);
  });

  test("finance can access export center and still sees export actions", async ({ page }) => {
    await login(page, FINANCE_EMAIL, FINANCE_PASSWORD, "/reports/export");

    await expect(page).toHaveURL(/\/reports\/export$/);
    await expect(page.getByRole("button", { name: "Xuất báo cáo" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Lưu thành mẫu" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Biểu mẫu BHXH" })).toBeVisible();
  });

  test("admin still sees mutate actions on rewards and training screens", async ({ page }) => {
    await login(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/rewards");

    await expect(page.getByRole("button", { name: "Thêm quyết định" })).toBeVisible();

    await page.goto("/training");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: "Thêm khóa học" })).toBeVisible();
  });
});

