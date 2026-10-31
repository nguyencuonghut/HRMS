import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test("position screens and attachment tab survive token refresh through shared api client", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  let refreshCount = 0;
  const attempts = new Map<string, number>();

  await page.route("**/api/v1/auth/refresh", async (route) => {
    refreshCount += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "mock-position-refresh-token" }),
    });
  });

  await page.route("**/api/v1/departments**", async (route) => {
    const url = new URL(route.request().url());
    const key = `${url.pathname}?${url.searchParams.toString()}`;
    const attempt = (attempts.get(key) ?? 0) + 1;
    attempts.set(key, attempt);
    if (attempt === 1) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Không thể xác thực thông tin đăng nhập" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 10,
          code: "HR",
          name: "Khối Nhân sự",
          short_name: null,
          display_prefix: null,
          parent_id: null,
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          order_no: 1,
          is_active: true,
          created_at: "2026-01-01T00:00:00",
          updated_at: null,
        },
      ]),
    });
  });

  await page.route("**/api/v1/job-titles**", async (route) => {
    const url = new URL(route.request().url());
    const key = `${url.pathname}?${url.searchParams.toString()}`;
    const attempt = (attempts.get(key) ?? 0) + 1;
    attempts.set(key, attempt);
    if (attempt === 1) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Không thể xác thực thông tin đăng nhập" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 7,
          code: "HRM",
          name: "Chuyên viên nhân sự",
          level: 3,
          is_active: true,
          created_at: "2026-01-01T00:00:00",
          updated_at: null,
        },
      ]),
    });
  });

  await page.route("**/api/v1/employee-code-rules/sequences**", async (route) => {
    const url = new URL(route.request().url());
    const key = `${url.pathname}?${url.searchParams.toString()}`;
    const attempt = (attempts.get(key) ?? 0) + 1;
    attempts.set(key, attempt);
    if (attempt === 1) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Không thể xác thực thông tin đăng nhập" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/v1/job-positions**", async (route) => {
    const url = new URL(route.request().url());
    const key = `${url.pathname}?${url.searchParams.toString()}`;
    const attempt = (attempts.get(key) ?? 0) + 1;
    attempts.set(key, attempt);
    if (attempt === 1) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Không thể xác thực thông tin đăng nhập" }),
      });
      return;
    }

    // PositionListView.loadData() gọi thêm endpoint này; không giả lập thì lần thử lại đi tới backend thật cùng token giả (401).
    if (url.pathname.endsWith("/job-positions/probation-legal-groups/options")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (url.pathname.endsWith("/job-positions")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 21,
            code: "HR_EXEC",
            name: "Chuyên viên HR",
            department_id: 10,
            department_name: "Khối Nhân sự",
            job_title_id: 7,
            job_title_name: "Chuyên viên nhân sự",
            bhxh_allowance: 0,
            non_bhxh_allowance: 0,
            probation_legal_group: null,
            probation_legal_group_label: null,
            probation_days_limit: null,
            assigned_department_ids: [10],
            assigned_departments: [{ id: 10, code: "HR", name: "Khối Nhân sự" }],
            is_shared: false,
            is_active: true,
            created_at: "2026-01-01T00:00:00",
            updated_at: null,
          },
        ]),
      });
      return;
    }

    if (url.pathname.endsWith("/job-positions/21")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 21,
          code: "HR_EXEC",
          name: "Chuyên viên HR",
          department_id: 10,
          job_title_id: 7,
          default_grade: 1,
          bhxh_allowance: 0,
          non_bhxh_allowance: 0,
          department_name: "Khối Nhân sự",
          probation_legal_group: null,
          probation_legal_group_label: null,
          probation_days_limit: null,
          assigned_department_ids: [10],
          assigned_departments: [{ id: 10, code: "HR", name: "Khối Nhân sự" }],
          is_shared: false,
          description: "Theo dõi hồ sơ nhân sự",
          requirements: "Kinh nghiệm 2 năm",
          is_active: true,
          created_at: "2026-01-01T00:00:00",
          updated_at: null,
        }),
      });
      return;
    }

    if (url.pathname.endsWith("/job-positions/21/attachments")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 301,
            file_name: "hr-guideline.docx",
            file_path: "attachments/hr-guideline.docx",
            file_size: 2048,
            uploaded_at: "2026-06-02T10:00:00",
            download_url: "http://example.test/hr-guideline.docx",
          },
        ]),
      });
      return;
    }

    await route.continue();
  });

  await page.getByRole("link", { name: "Vị trí công việc" }).click();
  await page.waitForURL(/\/org\/positions$/);

  await expect(page.getByRole("heading", { name: "Vị trí công việc" })).toBeVisible();
  await expect(page.getByText("Chuyên viên HR")).toBeVisible();
  await expect(page.locator(".p-toast-message").filter({ hasText: "Không thể xác thực thông tin đăng nhập" })).toHaveCount(0);
  expect(refreshCount).toBe(1);

  await page.locator(".action-cell button").first().click();
  await expect(page.getByText("Chi tiết vị trí công việc")).toBeVisible();
  await page.getByRole("tab", { name: "Tài liệu đính kèm" }).click();
  await expect(page.getByText("hr-guideline.docx")).toBeVisible();
  await expect(page.locator(".p-toast-message").filter({ hasText: "Không thể xác thực thông tin đăng nhập" })).toHaveCount(0);
  expect(refreshCount).toBe(3);
});
