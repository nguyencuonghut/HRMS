import { expect, test, type Page } from "@playwright/test";

const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";

async function login(page: Page, email = LINE_MANAGER_EMAIL, password = LINE_MANAGER_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByPlaceholder("Nhập mật khẩu").fill(password);

  const loginMeResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await loginMeResponse;
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports)/);
}

test.describe("Permission visibility", () => {
  test("line manager sidebar and report hub only expose allowed entries", async ({ page }) => {
    await login(page);

    const nav = page.locator("nav");
    await expect(nav.locator('a[href="/employees"]')).toBeVisible();
    await expect(nav.locator('a[href="/performance"]')).toBeVisible();

    await nav.locator(".menu-toggle", { hasText: "Nghỉ phép" }).click();
    await expect(nav.locator('a[href="/leaves"]')).toBeVisible();

    await expect(nav.locator('a[href="/contracts"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/insurance"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/salary"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/recruitment/jr"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/admin/users"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/admin/roles"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/admin/audit-logs"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/data/import"]')).toBeVisible();

    await page.goto("/reports");
    await page.waitForLoadState("networkidle");

    const main = page.locator("#main-content");
    await expect(main.getByRole("link", { name: /Dashboard tổng quan/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo nhân sự/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Thử việc & onboarding/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo nghỉ phép/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo hiệu suất \/ KPI/i })).toBeVisible();

    await expect(main.getByRole("link", { name: /Bảo hiểm/i })).toHaveCount(0);
    await expect(main.getByRole("link", { name: /Báo cáo hợp đồng/i })).toHaveCount(0);
    await expect(main.getByRole("link", { name: /Báo cáo tuyển dụng/i })).toHaveCount(0);
    await expect(main.getByRole("link", { name: /Báo cáo đào tạo/i })).toHaveCount(0);
    await expect(main.getByRole("link", { name: /Khen thưởng & Kỷ luật/i })).toHaveCount(0);
  });

  test("line manager cannot open guarded contracts route directly", async ({ page }) => {
    await login(page);

    await page.goto("/contracts");
    await page.waitForURL("**/forbidden");
    await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
  });
});
