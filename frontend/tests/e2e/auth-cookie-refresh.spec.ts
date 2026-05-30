import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test("login attaches access token for /auth/me and restores session via refresh cookie", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);

  const loginMeResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await loginMeResponse;
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  const refreshResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/refresh") && response.status() === 200;
  });
  const reloadMeResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.reload();
  await refreshResponse;
  await reloadMeResponse;

  await expect(page).toHaveURL(/\/(dashboard|reports\/dashboard)/);
});
