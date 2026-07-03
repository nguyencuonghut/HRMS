import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";
const EMPLOYEE_ID = 14;

async function login(page: Page, redirect = `/employees/${EMPLOYEE_ID}`) {
  await page.goto(`/login?redirect=${encodeURIComponent(redirect)}`);
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(new RegExp(`/employees/${EMPLOYEE_ID}`));
}

test("employee relatives tab shows per-relative health care participation", async ({ page }) => {
  await login(page);
  await page.waitForLoadState("networkidle");

  await page.getByRole("tab", { name: "Người thân" }).click();
  await expect(page.getByText("Danh sách người thân")).toBeVisible();

  const childCoveredRow = page.locator("tbody tr").filter({ hasText: "Tạ Gia Bảo" }).first();
  await expect(childCoveredRow).toBeVisible();
  await expect(childCoveredRow.getByText("Tham gia")).toBeVisible();

  const parentUncoveredRow = page.locator("tbody tr").filter({ hasText: "Tạ Văn Hùng" }).first();
  await expect(parentUncoveredRow).toBeVisible();
  await expect(parentUncoveredRow.getByText("Không")).toBeVisible();

  await childCoveredRow.locator("button").first().click();
  const dialog = page.getByRole("dialog", { name: "Cập nhật người thân" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Tham gia CSSK")).toBeVisible();
  await expect(
    dialog.getByText("Chỉ bật khi nhân viên đã đăng ký “Tham gia CSSK cho người thân” ở tab Bảo hiểm."),
  ).toBeVisible();
});
