import { expect, test } from "@playwright/test";

const users = [
  { email: "admin@hrms.local", password: "Hrms@2026", shouldSeeSettings: true },
  { email: "hrmanager@hrms.local", password: "Hrms@2026", shouldSeeSettings: true },
  { email: "hrofficer@hrms.local", password: "Hrms@2026", shouldSeeSettings: true },
  { email: "finance@hrms.local", password: "Hrms@2026", shouldSeeSettings: false },
  { email: "linemanager@hrms.local", password: "Hrms@2026", shouldSeeSettings: false },
];

for (const user of users) {
  test(`settings permission matrix: ${user.email}`, async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(user.email);
    await page.getByPlaceholder("Nhập mật khẩu").fill(user.password);
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await page.waitForLoadState("networkidle");

    const nav = page.locator("nav");
    const settingsGroup = nav.getByText("Cài đặt", { exact: true });
    const systemLink = nav.locator('a[href="/settings"]');
    const notificationsLink = nav.locator('a[href="/settings/notifications"]');

    if (user.shouldSeeSettings) {
      await expect(settingsGroup).toBeVisible();
      await nav.locator(".menu-toggle", { hasText: "Cài đặt" }).click();
      await expect(systemLink).toBeVisible();
      await expect(notificationsLink).toBeVisible();

      await systemLink.click();
      await page.waitForURL(/\/settings$/);
      await expect(page.getByRole("heading", { name: "Cài đặt hệ thống" })).toBeVisible();

      await notificationsLink.click();
      await page.waitForURL(/\/settings\/notifications$/);
      await expect(page.getByRole("heading", { name: "Cài đặt thông báo" })).toBeVisible();
    } else {
      await expect(settingsGroup).toHaveCount(0);
      await expect(systemLink).toHaveCount(0);
      await expect(notificationsLink).toHaveCount(0);

      await page.goto("/settings");
      await page.waitForURL("**/forbidden");
      await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();

      await page.goto("/settings/notifications");
      await page.waitForURL("**/forbidden");
      await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
    }
  });
}
