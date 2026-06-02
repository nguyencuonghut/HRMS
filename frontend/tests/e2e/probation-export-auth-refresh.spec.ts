import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test("probation export uses shared api client and refreshes instead of reading localStorage token", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  let refreshCount = 0;
  let exportAttempts = 0;

  await page.route("**/api/v1/auth/refresh", async (route) => {
    refreshCount += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "mock-probation-export-refresh-token" }),
    });
  });

  await page.route("**/api/v1/departments**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: 10, name: "Khối Nhân sự" },
      ]),
    });
  });

  await page.route("**/api/v1/reports/probation/active**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    });
  });

  await page.route("**/api/v1/reports/probation/history**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        period_start: "2026-05-01",
        period_end: "2026-05-31",
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
      }),
    });
  });

  await page.route("**/api/v1/reports/probation/checklist-completion**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        period_start: "2026-05-01",
        period_end: "2026-05-31",
        items: [],
      }),
    });
  });

  await page.route("**/api/v1/reports/probation/pass-rate**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        period_start: "2026-05-01",
        period_end: "2026-05-31",
        overall: {
          group_id: null,
          group_name: "Tổng",
          passed: 0,
          failed: 0,
          extended: 0,
          total_decided: 0,
          pass_rate: null,
        },
        by_department: [],
        by_position: [],
        monthly_trend: [],
      }),
    });
  });

  await page.route("**/api/v1/reports/probation/failure-reasons**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_failed: 0,
        reasons: [],
        raw_comments: [],
      }),
    });
  });

  await page.route("**/api/v1/reports/probation/export**", async (route) => {
    exportAttempts += 1;
    if (exportAttempts === 1) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Không thể xác thực thông tin đăng nhập" }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      headers: {
        "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content-disposition": 'attachment; filename="probation.xlsx"',
      },
      body: "fake-xlsx-binary",
    });
  });

  await page.getByRole("link", { name: "Thử việc & onboarding" }).click();
  await page.waitForURL(/\/reports\/probation$/);

  await page.getByPlaceholder("Từ ngày").fill("01/05/2026");
  await page.getByPlaceholder("Đến ngày").fill("31/05/2026");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất Excel" }).click();
  const download = await downloadPromise;

  await expect(page.locator(".p-toast-message").filter({ hasText: "Không thể xác thực thông tin đăng nhập" })).toHaveCount(0);
  expect(download.suggestedFilename()).toContain("bc_thu_viec_2026-05-01_2026-05-31");
  expect(refreshCount).toBe(1);
  expect(exportAttempts).toBe(2);
});
