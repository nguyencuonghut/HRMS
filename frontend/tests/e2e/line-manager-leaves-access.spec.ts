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

test("line manager can open all leave screens without redirecting to forbidden", async ({ page }) => {
  const leaveTypeResponses: Array<{ url: string; status: number }> = [];
  page.on("response", (response) => {
    if (response.url().includes("/api/v1/lookups/leave-types")) {
      leaveTypeResponses.push({ url: response.url(), status: response.status() });
    }
  });

  await login(page);

  const nav = page.locator("nav");
  await nav.locator(".menu-toggle", { hasText: "Nghỉ phép" }).click();

  const cases = [
    {
      href: "/leave-entitlements",
      url: /\/leave-entitlements$/,
      heading: "Số ngày phép",
      apiFragment: "/api/v1/leave-entitlements",
    },
    {
      href: "/leaves",
      url: /\/leaves$/,
      heading: "Ghi nhận nghỉ phép",
      apiFragment: "/api/v1/leave-records",
    },
    {
      href: "/leave-reports",
      url: /\/leave-reports$/,
      heading: "Báo cáo nghỉ phép",
      apiFragment: "/api/v1/leave-reports/employee-summary",
    },
  ] as const;

  for (const item of cases) {
    const responsePromise = page.waitForResponse((response) => {
      return response.url().includes(item.apiFragment) && response.status() === 200;
    });
    await nav.locator(`a[href="${item.href}"]`).click();
    await responsePromise;
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(item.url);
    await expect(page.getByRole("heading", { name: item.heading })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toHaveCount(0);
  }

  expect(leaveTypeResponses.length).toBeGreaterThan(0);
  expect(
    leaveTypeResponses.every((item) => item.status === 200),
    `Leave type lookup failed: ${JSON.stringify(leaveTypeResponses)}`,
  ).toBeTruthy();
});
