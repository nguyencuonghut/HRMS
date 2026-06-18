import { expect, test, type Page } from "@playwright/test";

const HR_OFFICER_EMAIL = process.env.E2E_HR_OFFICER_EMAIL || "hrofficer@hrms.local";
const HR_OFFICER_PASSWORD = process.env.E2E_HR_OFFICER_PASSWORD || "Hrms@2026";

async function login(page: Page, email = HR_OFFICER_EMAIL, password = HR_OFFICER_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByPlaceholder("Nhập mật khẩu").fill(password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports\/insurance|reports\/contracts)/);
}

test.describe("Report permission aliases", () => {
  test("hr officer can access insurance and contract reports with :view permissions", async ({ page }) => {
    await login(page);

    await page.goto("/reports/insurance");
    await page.waitForLoadState("networkidle");
    await expect(
      page.locator("#main-content").getByRole("heading", { name: "Phân tích bảo hiểm" }),
    ).toBeVisible();
    await expect(page).not.toHaveURL(/\/forbidden$/);

    await page.goto("/reports/contracts");
    await page.waitForLoadState("networkidle");
    await expect(
      page.locator("#main-content").getByRole("heading", { name: "Báo cáo hợp đồng" }),
    ).toBeVisible();
    await expect(page).not.toHaveURL(/\/forbidden$/);
  });
});
