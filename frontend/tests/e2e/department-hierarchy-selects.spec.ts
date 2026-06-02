import { expect, test, type Locator, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);
}

async function expectDepartmentHierarchy(select: Locator, page: Page) {
  await select.click();
  const overlay = page.locator(".p-select-overlay:visible").last();
  await expect(overlay.getByText("Phòng kiểm soát", { exact: true })).toBeVisible();
  await expect(overlay.getByText("-- Bộ phận IT", { exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
}

test.describe("Department hierarchy in department selects", () => {
  test("renders parent-child labels on dashboard, export center, and onboarding filters", async ({
    page,
  }) => {
    await login(page);

    await page.goto("/reports/dashboard");
    await page.waitForLoadState("networkidle");
    await expectDepartmentHierarchy(
      page.locator(".dashboard-toolbar .p-select").nth(2),
      page,
    );

    await page.goto("/reports/export");
    await page.waitForLoadState("networkidle");
    await expectDepartmentHierarchy(
      page.locator(".export-filter-panel .p-select").nth(2),
      page,
    );

    await page.goto("/employees/onboarding");
    await page.waitForLoadState("networkidle");
    await expectDepartmentHierarchy(
      page.locator(".toolbar .p-select").nth(1),
      page,
    );
  });
});
