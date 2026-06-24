import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page, redirect = "/reports/hr") {
  await page.goto(`/login?redirect=${encodeURIComponent(redirect)}`);
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(reports\/hr|catalog\/insurance|reports\/dashboard|dashboard)/);
}

test("retirement age policy config lives in catalog, not in HR report tab", async ({ page }) => {
  await login(page, "/reports/hr");

  await page.goto("/reports/hr");
  await page.getByRole("tab", { name: "Người lao động cao tuổi" }).click();
  await page.waitForLoadState("networkidle");

  await expect(page.getByText("Danh sách người lao động cao tuổi")).toBeVisible();
  await expect(page.getByText("Policy áp dụng")).toBeVisible();
  await expect(page.getByRole("button", { name: "Policy tuổi nghỉ hưu" })).toHaveCount(0);
  await expect(page.getByText("Lịch sử policy")).toHaveCount(0);

  await page.goto("/catalog/insurance");
  await page.waitForLoadState("networkidle");

  await expect(page.getByRole("heading", { name: "Policy tuổi nghỉ hưu" })).toBeVisible();
  await expect(page.getByText("Lịch sử policy")).toBeVisible();
  await expect(page.getByRole("button", { name: "Thêm policy tuổi nghỉ hưu" })).toBeVisible();
});
