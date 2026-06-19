import { expect, test, type Page } from "@playwright/test";

async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@hrms.local");
  await page.getByPlaceholder("Nhập mật khẩu").fill("Hrms@2026");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForLoadState("networkidle");
}

async function expectMenuLinkActive(page: Page, href: string, active: boolean) {
  const link = page.locator(`nav a[href="${href}"]`).first();
  if (active) {
    await expect(link).toHaveClass(/router-link-active/);
  } else {
    await expect(link).not.toHaveClass(/router-link-active/);
  }
}

test("submenu uses longest matching route so only one child is active", async ({ page }) => {
  await loginAsAdmin(page);

  await page.goto("/insurance/reports");
  await page.waitForLoadState("networkidle");
  await expectMenuLinkActive(page, "/insurance", false);
  await expectMenuLinkActive(page, "/insurance/reports", true);

  await page.goto("/salary/bhxh-adjustments");
  await page.waitForLoadState("networkidle");
  await expectMenuLinkActive(page, "/salary", false);
  await expectMenuLinkActive(page, "/salary/bhxh-adjustments", true);

  await page.goto("/reports/insurance");
  await page.waitForLoadState("networkidle");
  await expectMenuLinkActive(page, "/reports", false);
  await expectMenuLinkActive(page, "/reports/insurance", true);

  await page.goto("/catalog/insurance");
  await page.waitForLoadState("networkidle");
  await expectMenuLinkActive(page, "/catalog", false);
  await expectMenuLinkActive(page, "/catalog/insurance", true);

  await page.goto("/settings/notifications");
  await page.waitForLoadState("networkidle");
  await expectMenuLinkActive(page, "/settings", false);
  await expectMenuLinkActive(page, "/settings/notifications", true);

  await page.goto("/employees/onboarding");
  await page.waitForLoadState("networkidle");
  await expectMenuLinkActive(page, "/employees", false);
  await expectMenuLinkActive(page, "/employees/onboarding", true);
});
