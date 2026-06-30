import { expect, test, type Page } from "@playwright/test";

const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(LINE_MANAGER_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(LINE_MANAGER_PASSWORD);

  const meResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await meResponse;
  await page.waitForLoadState("networkidle");
}

test("line manager can open rewards page without forbidden redirect when lacking disciplines:view", async ({ page }) => {
  const trackedResponses: Array<{ url: string; status: number }> = [];
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/v1/rewards") || url.includes("/api/v1/disciplines")) {
      trackedResponses.push({ url, status: response.status() });
    }
  });

  await login(page);

  const nav = page.locator("nav");
  const rewardsResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/rewards?") && response.status() === 200;
  });
  await nav.locator('a[href="/rewards"]').click();
  await rewardsResponsePromise;
  await page.waitForLoadState("networkidle");

  await expect(page).toHaveURL(/\/rewards$/);
  await expect(page.getByRole("heading", { name: "Khen thưởng & Kỷ luật" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Khen thưởng" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Kỷ luật" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toHaveCount(0);

  expect(
    trackedResponses.filter((item) => item.url.includes("/api/v1/disciplines")),
    "Rewards page should not query disciplines API when user lacks disciplines:view",
  ).toHaveLength(0);
  expect(trackedResponses.every((item) => item.status < 400)).toBeTruthy();
});
