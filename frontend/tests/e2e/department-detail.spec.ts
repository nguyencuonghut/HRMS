import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test("department list navigates to detail page and renders summary/direct employees", async ({
  page,
}) => {
  let detailRequestCount = 0;
  let currentHead = {
    id: 501,
    department_id: 901,
    employee_id: 1201,
    head_role_label: "Trưởng phòng kiểm soát",
    display_position_label: "Trưởng phòng kiểm soát",
    effective_from: "2026-01-01",
    effective_to: null,
    is_current: true,
    employee: {
      id: 1201,
      display_code: "KS001",
      full_name: "Nguyễn Văn Cường",
      status: "official",
      current_department_id: 901,
      current_department_name: "Phòng kiểm soát",
      current_job_position_id: 777,
      current_job_position_name: "Giám đốc khối kiểm soát",
      current_job_title_id: 31,
      current_job_title_name: "Trưởng phòng",
      is_cross_department_assignment: false,
    },
  };
  let lastHeadPayload: Record<string, unknown> | null = null;

  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  await page.route("**/api/v1/departments/tree**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 901,
          code: "KS",
          name: "Phòng kiểm soát",
          short_name: "KS",
          display_prefix: "KS",
          parent_id: null,
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          order_no: 1,
          is_active: true,
          created_at: "2026-01-01T00:00:00",
          updated_at: null,
          children: [],
        },
      ]),
    });
  });

  await page.route("**/api/v1/departments/901/detail", async (route) => {
    detailRequestCount += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        department: {
          id: 901,
          code: "KS",
          name: "Phòng kiểm soát",
          short_name: "KS",
          display_prefix: "KS",
          parent_id: null,
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          order_no: 1,
          is_active: true,
          created_at: "2026-01-01T00:00:00",
          updated_at: null,
        },
        parent: null,
        summary: {
          direct_headcount: 3,
          total_headcount: 5,
          direct_child_count: 2,
          job_position_count: 4,
        },
        direct_employees: [
          {
            id: 1201,
            display_code: "KS001",
            full_name: "Nguyễn Văn Cường",
            status: "official",
            start_date: "2024-01-10",
            job_title_name: "Trưởng phòng",
            job_position_name: "Giám đốc khối kiểm soát",
          },
        ],
      }),
    });
  });

  await page.route("**/api/v1/departments/901/head", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(currentHead),
      });
      return;
    }
    if (method === "PUT") {
      lastHeadPayload = route.request().postDataJSON() as Record<string, unknown>;
      currentHead = {
        ...currentHead,
        employee_id: 1302,
        head_role_label: "Phụ trách kiểm soát",
        display_position_label: "Phụ trách kiểm soát",
        effective_from: "2026-01-01",
        employee: {
          id: 1302,
          display_code: "KS002",
          full_name: "Trần Thị Lan",
          status: "official",
          current_department_id: 902,
          current_department_name: "Ban dự án",
          current_job_position_id: 778,
          current_job_position_name: "Phó trưởng phòng kiểm soát",
          current_job_title_id: 32,
          current_job_title_name: "Phó phòng",
          is_cross_department_assignment: true,
        },
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(currentHead),
      });
      return;
    }
    if (method === "DELETE") {
      currentHead = null as never;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ message: "Đã gỡ người đứng đầu hiện hành" }),
      });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/v1/employees/lookup**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 1302,
          employee_seq: 2,
          display_code: "KS002",
          full_name: "Trần Thị Lan",
          status: "official",
        },
      ]),
    });
  });

  await page.goto("/org/departments");
  await expect(page.getByRole("heading", { name: "Phòng / Ban" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Phòng kiểm soát" })).toBeVisible();

  await page.getByRole("button", { name: "Phòng kiểm soát" }).click();

  await page.waitForURL(/\/org\/departments\/901$/);
  await expect(page.getByRole("heading", { name: "Phòng kiểm soát" })).toBeVisible();
  await expect(page.getByText("KS · Phòng")).toBeVisible();

  const summaryCards = page.locator(".dept-summary-card");
  await expect(summaryCards).toHaveCount(4);
  await expect(summaryCards.nth(0)).toContainText("Nhân sự trực tiếp");
  await expect(summaryCards.nth(0)).toContainText("3");
  await expect(summaryCards.nth(1)).toContainText("Nhân sự toàn cây");
  await expect(summaryCards.nth(1)).toContainText("5");
  await expect(summaryCards.nth(2)).toContainText("Đơn vị con trực tiếp");
  await expect(summaryCards.nth(2)).toContainText("2");
  await expect(summaryCards.nth(3)).toContainText("Vị trí công việc");
  await expect(summaryCards.nth(3)).toContainText("4");

  const headCard = page.locator(".dept-head-card");
  await expect(page.getByRole("cell", { name: "KS001" })).toBeVisible();
  await expect(page.getByRole("table").getByRole("button", { name: "Nguyễn Văn Cường" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Giám đốc khối kiểm soát" })).toBeVisible();
  await expect(page.getByRole("table").getByText("Chính thức")).toBeVisible();
  await expect(headCard.getByRole("heading", { name: "Người đứng đầu hiện tại" })).toBeVisible();
  await expect(headCard.getByRole("button", { name: "Nguyễn Văn Cường" })).toBeVisible();
  await expect(headCard.getByText("Trưởng phòng kiểm soát")).toBeVisible();

  await headCard.getByRole("button", { name: "Thay đổi" }).click();
  await page.getByPlaceholder("Tìm theo mã nhân viên, họ tên hoặc mã số nhân viên").fill("Lan");
  await page.getByText("Trần Thị Lan").click();
  await page.getByPlaceholder("VD: Trưởng phòng, Phụ trách khối...").fill("Phụ trách kiểm soát");
  await page.getByRole("button", { name: "Lưu người đứng đầu" }).click();

  await expect(headCard.getByRole("button", { name: "Trần Thị Lan" })).toBeVisible();
  await expect(headCard.getByText("Phụ trách kiểm soát")).toBeVisible();
  await expect(headCard.getByText("Nhân sự này đang thuộc đơn vị")).toBeVisible();

  await headCard.getByRole("button", { name: "Gỡ" }).click();
  await page.getByRole("alertdialog", { name: "Gỡ người đứng đầu hiện hành" }).getByRole("button", { name: "Gỡ" }).click();
  await expect(headCard.getByText("Đơn vị này chưa được gán người đứng đầu.")).toBeVisible();

  expect(detailRequestCount).toBe(1);
  expect(lastHeadPayload).toEqual({
    employee_id: 1302,
    head_role_label: "Phụ trách kiểm soát",
    effective_from: "2026-01-01",
  });
});
