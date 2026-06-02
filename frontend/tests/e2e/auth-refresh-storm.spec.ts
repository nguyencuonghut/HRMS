import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test("concurrent 401s share one refresh and do not surface auth toast", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  let refreshCount = 0;
  const reportAttempts = new Map<string, number>();

  await page.route("**/api/v1/auth/refresh", async (route) => {
    refreshCount += 1;
    if (refreshCount === 1) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ access_token: "mock-refreshed-access-token" }),
      });
      return;
    }

    await route.fulfill({
      status: 429,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Too Many Requests" }),
    });
  });

  await page.route("**/api/v1/reports/probation/**", async (route) => {
    const url = new URL(route.request().url());
    const key = `${url.pathname}?${url.searchParams.toString()}`;
    const attempt = (reportAttempts.get(key) ?? 0) + 1;
    reportAttempts.set(key, attempt);

    if (attempt === 1) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Không thể xác thực thông tin đăng nhập" }),
      });
      return;
    }

    if (url.pathname.endsWith("/active")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              employee_id: 1,
              employee_name: "Nguyễn Văn Cường",
              employee_code: "EMP001",
              department_id: 1,
              department_name: "Khối Nhân sự",
              probation_start_date: "2026-05-01",
              probation_end_date: "2026-07-01",
              days_remaining: 29,
              urgency: "normal",
              onboarding_status: "in_progress",
              completion_pct: 80,
              evaluation_result: "pending",
            },
          ],
          total: 1,
        }),
      });
      return;
    }

    if (url.pathname.endsWith("/history")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_start: null,
          period_end: null,
          items: [
            {
              employee_id: 1,
              employee_name: "Nguyễn Văn Cường",
              employee_code: "EMP001",
              employee_status: "probation",
              department_id: 1,
              department_name: "Khối Nhân sự",
              probation_start_date: "2026-05-01",
              probation_end_date: "2026-07-01",
              days_remaining: 29,
              onboarding_status: "in_progress",
              completion_pct: 80,
              evaluation_result: "pending",
              evaluation_status: "draft",
            },
          ],
          total: 1,
          page: 1,
          page_size: 10,
        }),
      });
      return;
    }

    if (url.pathname.endsWith("/checklist-completion")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_start: "2000-01-01",
          period_end: "2026-06-02",
          items: [
            {
              department_id: 1,
              department_name: "Khối Nhân sự",
              total_checklists: 1,
              completed_count: 1,
              completion_rate: 100,
              avg_completion_pct: 100,
            },
          ],
        }),
      });
      return;
    }

    if (url.pathname.endsWith("/pass-rate")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          period_start: "2000-01-01",
          period_end: "2026-06-02",
          overall: {
            group_id: null,
            group_name: "Tổng",
            passed: 1,
            failed: 0,
            extended: 0,
            total_decided: 1,
            pass_rate: 100,
          },
          by_department: [],
          by_position: [],
          monthly_trend: [],
        }),
      });
      return;
    }

    if (url.pathname.endsWith("/failure-reasons")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_failed: 0,
          reasons: [],
          raw_comments: [],
        }),
      });
      return;
    }

    await route.continue();
  });

  await page.getByRole("link", { name: "Thử việc & onboarding" }).click();
  await page.waitForURL(/\/reports\/probation$/);

  await expect(page.getByText("Tỷ lệ hoàn thành checklist hội nhập theo phòng ban")).toBeVisible();
  await expect(page.getByText("Nguyễn Văn Cường")).toBeVisible();
  await expect(page.locator(".p-toast-message").filter({ hasText: "Không thể xác thực thông tin đăng nhập" })).toHaveCount(0);
  expect(refreshCount).toBe(1);
});
