import { expect, test } from "@playwright/test";

test("finance lands on an allowed screen after login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("finance@hrms.local");
  await page.getByPlaceholder("Nhập mật khẩu").fill("Hrms@2026");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForLoadState("networkidle");

  await expect(page).not.toHaveURL(/\/forbidden$/);
  await expect(page).toHaveURL(/\/(reports|insurance|salary)/);
});
