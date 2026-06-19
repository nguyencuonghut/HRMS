import { expect, test } from "@playwright/test";

test("finance can open every visible insurance/salary/report menu without forbidden redirect", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("finance@hrms.local");
  await page.getByPlaceholder("Nhập mật khẩu").fill("Hrms@2026");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForLoadState("networkidle");

  const nav = page.locator("nav");

  await expect(nav.locator('a[href="/catalog"]')).toHaveCount(0);

  await nav.locator(".menu-toggle", { hasText: "Bảo hiểm BHXH" }).click();
  await expect(nav.locator('a[href="/insurance"]')).toBeVisible();
  await nav.locator('a[href="/insurance"]').click();
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveURL(/\/insurance$/);
  await expect(page.getByRole("heading", { name: "Bảo hiểm BHXH" })).toBeVisible();

  await nav.locator(".menu-toggle", { hasText: "Lương BHXH" }).click();
  await expect(nav.locator('a[href="/salary"]')).toBeVisible();
  await nav.locator('a[href="/salary"]').click();
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveURL(/\/salary$/);
  await expect(page.getByRole("heading", { name: "Lương BHXH" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Mức lương BHXH" })).toBeVisible();

  await page.goto("/reports/insurance");
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveURL(/\/reports\/insurance$/);
  await expect(page.getByRole("heading", { name: "Phân tích bảo hiểm" })).toBeVisible();

  await page.goto("/reports/export");
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveURL(/\/reports\/export$/);
  await expect(page.getByRole("heading", { name: "Xuất báo cáo" })).toBeVisible();

  await page.goto("/catalog/insurance");
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveURL(/\/catalog\/insurance$/);
  await expect(page.getByRole("heading", { name: "Cấu hình BHXH dùng chung" })).toBeVisible();

  await page.goto("/catalog/bhyt-clinics");
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveURL(/\/catalog\/bhyt-clinics$/);
  await expect(page.getByRole("heading", { name: "Danh mục bệnh viện KCB" })).toBeVisible();

  await expect(page).not.toHaveURL(/\/forbidden$/);
});
