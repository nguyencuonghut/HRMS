import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page, email = ADMIN_EMAIL, password = ADMIN_PASSWORD) {
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

test("admin can manage document checklist catalog in other business catalog view", async ({ page }) => {
  await login(page);

  await page.goto("/catalog/other-business");
  await page.waitForLoadState("networkidle");

  await page.getByRole("tab", { name: "Checklist hồ sơ" }).click();

  const suffix = Date.now().toString().slice(-6);
  const code = `test_docchk_ui_${suffix}`;
  const name = `Checklist hồ sơ UI ${suffix}`;
  const updatedName = `${name} updated`;

  await page.getByRole("button", { name: "Thêm checklist hồ sơ" }).click();
  const dialog = page.getByRole("dialog", { name: "Thêm checklist hồ sơ" });
  await expect(dialog).toBeVisible();

  await dialog.locator(".field").filter({ hasText: "Mã" }).getByRole("textbox").fill(code);
  await dialog.locator(".field").filter({ hasText: "Tên" }).getByRole("textbox").fill(name);
  await dialog.locator(".field").filter({ hasText: "Mô tả" }).getByRole("textbox").fill("Tạo từ Playwright");
  await dialog.locator(".field").filter({ hasText: "Thứ tự" }).getByRole("spinbutton").fill("77");
  await dialog.getByRole("button", { name: "Tạo mới" }).click();

  await expect(page.getByText(name)).toBeVisible();

  const row = page.locator("tr", { hasText: name }).first();
  await row.getByRole("button").nth(0).click();
  const editDialog = page.getByRole("dialog", { name: "Chỉnh sửa checklist hồ sơ" });
  await expect(editDialog).toBeVisible();
  await editDialog.locator(".field").filter({ hasText: "Tên" }).getByRole("textbox").fill(updatedName);
  await editDialog.getByRole("button", { name: "Lưu thay đổi" }).click();

  await expect(page.getByText(updatedName)).toBeVisible();

  const updatedRow = page.locator("tr", { hasText: updatedName }).first();
  await updatedRow.getByRole("button").nth(1).click();
  await page.getByRole("button", { name: "Khóa" }).click();

  await expect(page.getByText(updatedName)).toHaveCount(0);
});
