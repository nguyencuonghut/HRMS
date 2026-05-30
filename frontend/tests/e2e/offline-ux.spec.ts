import { expect, test } from "@playwright/test";

test("offline banner and login message reflect connectivity status", async ({ page, context }) => {
  await page.goto("/login");
  await expect(page.getByLabel("Email")).toBeVisible();

  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));

  await expect(page.getByRole("status")).toContainText("Mất kết nối Internet");

  await page.getByLabel("Email").fill("admin@hrms.local");
  await page.getByPlaceholder("Nhập mật khẩu").fill("Hrms@2026");
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page.getByText("Không có kết nối Internet. Vui lòng kiểm tra mạng và thử lại.")).toBeVisible();

  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));

  await expect(page.getByRole("status")).toContainText("Kết nối Internet đã được khôi phục");
});
