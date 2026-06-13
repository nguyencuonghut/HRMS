import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

function toOrgChartHead(head: {
  employee_id: number;
  display_position_label: string;
  employee: {
    id: number;
    display_code: string;
    full_name: string;
    status: string;
    current_department_name: string | null;
    current_job_position_name: string | null;
    current_job_title_name: string | null;
    is_cross_department_assignment: boolean;
  };
}) {
  const parts = head.employee.full_name.split(" ").filter(Boolean);
  const avatarInitials =
    parts.length > 1
      ? `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
      : head.employee.full_name.slice(0, 1).toUpperCase();

  return {
    employee_id: head.employee_id,
    display_code: head.employee.display_code,
    full_name: head.employee.full_name,
    status: head.employee.status,
    display_position_label: head.display_position_label,
    current_department_name: head.employee.current_department_name,
    current_job_position_name: head.employee.current_job_position_name,
    current_job_title_name: head.employee.current_job_title_name,
    is_cross_department_assignment: head.employee.is_cross_department_assignment,
    avatar_preview_url: null,
    avatar_initials: avatarInitials,
  };
}

function toNullableOrgChartHead(
  head:
    | {
        employee_id: number;
        display_position_label: string;
        employee: {
          id: number;
          display_code: string;
          full_name: string;
          status: string;
          current_department_name: string | null;
          current_job_position_name: string | null;
          current_job_title_name: string | null;
          is_cross_department_assignment: boolean;
        };
      }
    | null,
) {
  return head ? toOrgChartHead(head) : null;
}

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
  const detail901 = {
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
    org_chart: {
      key: "dept-901",
      type: "department",
      department_id: 901,
      department_code: "KS",
      department_name: "Phòng kiểm soát",
      dept_type: "PHONG",
      dept_type_label: "Phòng",
      direct_headcount: 3,
      total_headcount: 5,
      head: currentHead,
      children: [
        {
          key: "dept-902",
          type: "department",
          department_id: 902,
          department_code: "KSNB",
          department_name: "Tổ kiểm soát nội bộ",
          dept_type: "TO",
          dept_type_label: "Tổ",
          direct_headcount: 2,
          total_headcount: 2,
          head: null,
          children: [],
        },
      ],
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
  };
  const detail902 = {
    department: {
      id: 902,
      code: "KSNB",
      name: "Tổ kiểm soát nội bộ",
      short_name: "KSNB",
      display_prefix: "KSNB",
      parent_id: 901,
      dept_type: "TO",
      dept_type_label: "Tổ",
      order_no: 2,
      is_active: true,
      created_at: "2026-01-01T00:00:00",
      updated_at: null,
    },
    parent: {
      id: 901,
      code: "KS",
      name: "Phòng kiểm soát",
      parent_id: null,
      dept_type: "PHONG",
      dept_type_label: "Phòng",
      is_active: true,
    },
    summary: {
      direct_headcount: 2,
      total_headcount: 2,
      direct_child_count: 0,
      job_position_count: 1,
    },
    org_chart: {
      key: "dept-902",
      type: "department",
      department_id: 902,
      department_code: "KSNB",
      department_name: "Tổ kiểm soát nội bộ",
      dept_type: "TO",
      dept_type_label: "Tổ",
      direct_headcount: 2,
      total_headcount: 2,
      head: null,
      children: [],
    },
    direct_employees: [],
  };

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
        ...detail901,
        org_chart: {
          ...detail901.org_chart,
          head: toNullableOrgChartHead(currentHead),
        },
      }),
    });
  });

  await page.route("**/api/v1/departments/902/detail", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(detail902),
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

  await page.route("**/api/v1/departments/902/head", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "null",
    });
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
          current_department_id: 902,
          current_department_name: "Ban dự án",
          current_job_position_id: 778,
          current_job_position_name: "Phó trưởng phòng kiểm soát",
          current_job_title_id: 32,
          current_job_title_name: "Phó phòng",
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
  const orgChartCard = page.locator(".dept-org-card");
  const directEmployeesCard = page.locator(".dept-employees-card");
  await expect(page.getByRole("cell", { name: "KS001" })).toBeVisible();
  await expect(directEmployeesCard.getByRole("button", { name: "Nguyễn Văn Cường" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Giám đốc khối kiểm soát" })).toBeVisible();
  await expect(directEmployeesCard.getByText("Chính thức")).toBeVisible();
  await expect(headCard.getByRole("heading", { name: "Người đứng đầu hiện tại" })).toBeVisible();
  await expect(headCard.getByRole("button", { name: "Nguyễn Văn Cường" })).toBeVisible();
  await expect(headCard.getByText("Trưởng phòng kiểm soát")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sơ đồ đơn vị" })).toBeVisible();
  await expect(orgChartCard.getByRole("button", { name: "Phòng kiểm soát" })).toBeVisible();
  await expect(orgChartCard.getByRole("button", { name: "Tổ kiểm soát nội bộ" })).toBeVisible();
  await expect(orgChartCard.getByText("Chưa gán người phụ trách")).toBeVisible();
  await expect(orgChartCard.getByText("Trực tiếp: 3")).toBeVisible();
  await expect(orgChartCard.getByText("Toàn cây: 5")).toBeVisible();

  await headCard.getByRole("button", { name: "Thay đổi" }).click();
  await page.getByPlaceholder("Tìm theo mã nhân viên, họ tên hoặc mã số nhân viên").fill("Lan");
  await page.getByText("Trần Thị Lan").click();
  const selectedCard = page.locator(".dept-head-selected");
  await expect(selectedCard.getByText("Nhân sự này đang thuộc đơn vị")).toBeVisible();
  await expect(selectedCard).toContainText("Ban dự án");
  await page.getByPlaceholder("VD: Trưởng phòng, Phụ trách khối...").fill("Phụ trách kiểm soát");
  await page.getByRole("button", { name: "Lưu người đứng đầu" }).click();

  await expect(headCard.getByRole("button", { name: "Trần Thị Lan" })).toBeVisible();
  await expect(headCard.getByText("Phụ trách kiểm soát")).toBeVisible();
  await expect(headCard.getByText("Nhân sự này đang thuộc đơn vị")).toBeVisible();

  await headCard.getByRole("button", { name: "Gỡ" }).click();
  await page.getByRole("alertdialog", { name: "Gỡ người đứng đầu hiện hành" }).getByRole("button", { name: "Gỡ" }).click();
  await expect(headCard.getByText("Đơn vị này chưa được gán người đứng đầu.")).toBeVisible();

  await orgChartCard.getByRole("button", { name: "Tổ kiểm soát nội bộ" }).click();
  await page.waitForURL(/\/org\/departments\/902$/);
  await expect(page.getByRole("heading", { name: "Tổ kiểm soát nội bộ" })).toBeVisible();
  await expect(page.getByText("KSNB · Tổ")).toBeVisible();
  await expect(page.getByText("Thuộc Phòng kiểm soát")).toBeVisible();

  expect(detailRequestCount).toBe(3);
  expect(lastHeadPayload).toEqual({
    employee_id: 1302,
    head_role_label: "Phụ trách kiểm soát",
    effective_from: "2026-01-01",
  });
});

test("department detail shows retry state when current head cannot be loaded initially", async ({
  page,
}) => {
  let headRequestCount = 0;

  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  await page.route("**/api/v1/departments/901/detail", async (route) => {
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
          total_headcount: 3,
          direct_child_count: 0,
          job_position_count: 1,
        },
        org_chart: {
          key: "dept-901",
          type: "department",
          department_id: 901,
          department_code: "KS",
          department_name: "Phòng kiểm soát",
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          direct_headcount: 3,
          total_headcount: 3,
          head: null,
          children: [],
        },
        direct_employees: [],
      }),
    });
  });

  await page.route("**/api/v1/departments/901/head", async (route) => {
    headRequestCount += 1;
    if (headRequestCount <= 2) {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Mock head service error" }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
      }),
    });
  });

  await page.goto("/org/departments/901");

  const headCard = page.locator(".dept-head-card");
  await expect(headCard.getByText("Không tải được người đứng đầu hiện tại")).toBeVisible();
  await expect(headCard.getByText("Mock head service error")).toBeVisible();

  await headCard.getByRole("button", { name: "Tải lại" }).click();
  await expect(headCard.getByRole("button", { name: "Nguyễn Văn Cường" })).toBeVisible();
  expect(headRequestCount).toBeGreaterThanOrEqual(3);
});

test("org chart falls back to initials when avatar preview image fails", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  await page.route("**/api/v1/departments/903/detail", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        department: {
          id: 903,
          code: "AVT",
          name: "Phòng avatar",
          short_name: "AVT",
          display_prefix: "AVT",
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
          direct_headcount: 1,
          total_headcount: 1,
          direct_child_count: 0,
          job_position_count: 1,
        },
        org_chart: {
          key: "dept-903",
          type: "department",
          department_id: 903,
          department_code: "AVT",
          department_name: "Phòng avatar",
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          direct_headcount: 1,
          total_headcount: 1,
          head: {
            employee_id: 1401,
            display_code: "AVT001",
            full_name: "Lê Minh",
            status: "official",
            display_position_label: "Phụ trách",
            current_department_name: "Phòng avatar",
            current_job_position_name: "Phụ trách",
            current_job_title_name: null,
            is_cross_department_assignment: false,
            avatar_preview_url: "/api/v1/employees/1401/attachments/9/preview?token=broken",
            avatar_initials: "LM",
          },
          children: [],
        },
        direct_employees: [],
      }),
    });
  });

  await page.route("**/api/v1/departments/903/head", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 601,
        department_id: 903,
        employee_id: 1401,
        head_role_label: "Phụ trách",
        display_position_label: "Phụ trách",
        effective_from: "2026-01-01",
        effective_to: null,
        is_current: true,
        employee: {
          id: 1401,
          display_code: "AVT001",
          full_name: "Lê Minh",
          status: "official",
          current_department_id: 903,
          current_department_name: "Phòng avatar",
          current_job_position_id: 1,
          current_job_position_name: "Phụ trách",
          current_job_title_id: null,
          current_job_title_name: null,
          is_cross_department_assignment: false,
        },
      }),
    });
  });

  await page.route("**/api/v1/employees/1401/attachments/9/preview?token=broken", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "text/plain",
      body: "not found",
    });
  });

  await page.goto("/org/departments/903");

  const orgChartCard = page.locator(".dept-org-card");
  await expect(orgChartCard.getByRole("button", { name: "Phòng avatar" })).toBeVisible();
  await expect(orgChartCard.getByText("LM")).toBeVisible();
  await expect(orgChartCard.locator(".dept-org-avatar-image")).toHaveCount(0);
});

test("department detail cards keep inner padding from border", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  await page.route("**/api/v1/departments/904/detail", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        department: {
          id: 904,
          code: "PAD",
          name: "Phòng có padding",
          short_name: "PAD",
          display_prefix: "PAD",
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
          direct_headcount: 1,
          total_headcount: 1,
          direct_child_count: 0,
          job_position_count: 1,
        },
        org_chart: {
          key: "dept-904",
          type: "department",
          department_id: 904,
          department_code: "PAD",
          department_name: "Phòng có padding",
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          direct_headcount: 1,
          total_headcount: 1,
          head: null,
          children: [],
        },
        direct_employees: [],
      }),
    });
  });

  await page.route("**/api/v1/departments/904/head", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "null",
    });
  });

  await page.goto("/org/departments/904");

  const summaryCard = page.locator(".dept-summary-card").first();
  const headCard = page.locator(".dept-head-card");
  const orgCard = page.locator(".dept-org-card");
  const employeeCard = page.locator(".dept-employees-card");

  await expect(summaryCard).toBeVisible();
  await expect(headCard).toBeVisible();
  await expect(orgCard).toBeVisible();
  await expect(employeeCard).toBeVisible();

  for (const locator of [summaryCard, headCard, orgCard, employeeCard]) {
    const padding = await locator.evaluate((element) => {
      const style = window.getComputedStyle(element);
      return {
        top: Number.parseFloat(style.paddingTop),
        right: Number.parseFloat(style.paddingRight),
        bottom: Number.parseFloat(style.paddingBottom),
        left: Number.parseFloat(style.paddingLeft),
      };
    });

    expect(padding.top).toBeGreaterThanOrEqual(16);
    expect(padding.right).toBeGreaterThanOrEqual(16);
    expect(padding.bottom).toBeGreaterThanOrEqual(16);
    expect(padding.left).toBeGreaterThanOrEqual(16);
  }
});

test("head detail tiles use dark surface styling in dark mode", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  await page.route("**/api/v1/departments/905/detail", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        department: {
          id: 905,
          code: "DM",
          name: "Phòng dark mode",
          short_name: "DM",
          display_prefix: "DM",
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
          direct_headcount: 1,
          total_headcount: 1,
          direct_child_count: 0,
          job_position_count: 1,
        },
        org_chart: {
          key: "dept-905",
          type: "department",
          department_id: 905,
          department_code: "DM",
          department_name: "Phòng dark mode",
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          direct_headcount: 1,
          total_headcount: 1,
          head: null,
          children: [],
        },
        direct_employees: [],
      }),
    });
  });

  await page.route("**/api/v1/departments/905/head", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 701,
        department_id: 905,
        employee_id: 1501,
        head_role_label: "Giám đốc khối kiểm soát",
        display_position_label: "Giám đốc khối kiểm soát",
        effective_from: "2026-06-13",
        effective_to: null,
        is_current: true,
        employee: {
          id: 1501,
          display_code: "KS0001",
          full_name: "Tạ Văn Toại",
          status: "official",
          current_department_id: 905,
          current_department_name: "Phòng dark mode",
          current_job_position_id: 11,
          current_job_position_name: "Giám đốc khối kiểm soát",
          current_job_title_id: 21,
          current_job_title_name: "Trưởng phòng",
          is_cross_department_assignment: false,
        },
      }),
    });
  });

  await page.goto("/org/departments/905");

  const firstTile = page.locator(".dept-head-item").first();
  await expect(firstTile).toBeVisible();

  const style = await firstTile.evaluate((element) => {
    const computed = window.getComputedStyle(element);
    const rgb = computed.backgroundColor.match(/\d+/g) ?? [];
    return {
      backgroundColor: computed.backgroundColor,
      borderTopColor: computed.borderTopColor,
      rgbChannels: rgb.slice(0, 3).map((value) => Number.parseInt(value, 10)),
    };
  });

  expect(style.borderTopColor).not.toBe("rgba(0, 0, 0, 0)");
  expect(style.backgroundColor).not.toBe("rgb(255, 255, 255)");
  expect(style.rgbChannels.length).toBe(3);
  expect(Math.max(...style.rgbChannels)).toBeLessThan(140);
});

test("org chart nodes use tighter spacing and larger avatar", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);

  await page.route("**/api/v1/departments/906/detail", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        department: {
          id: 906,
          code: "ORG",
          name: "Phòng org chart",
          short_name: "ORG",
          display_prefix: "ORG",
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
          direct_headcount: 1,
          total_headcount: 2,
          direct_child_count: 1,
          job_position_count: 1,
        },
        org_chart: {
          key: "dept-906",
          type: "department",
          department_id: 906,
          department_code: "ORG",
          department_name: "Phòng org chart",
          dept_type: "PHONG",
          dept_type_label: "Phòng",
          direct_headcount: 1,
          total_headcount: 2,
          head: {
            employee_id: 1601,
            display_code: "ORG001",
            full_name: "Nguyễn Org",
            status: "official",
            display_position_label: "Phụ trách",
            current_department_name: "Phòng org chart",
            current_job_position_name: "Phụ trách",
            current_job_title_name: null,
            is_cross_department_assignment: false,
            avatar_preview_url: null,
            avatar_initials: "NO",
          },
          children: [],
        },
        direct_employees: [],
      }),
    });
  });

  await page.route("**/api/v1/departments/906/head", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "null",
    });
  });

  await page.goto("/org/departments/906");

  const node = page.locator(".dept-org-node").first();
  const avatar = node.locator(".dept-org-avatar");
  const headBlock = node.locator(".dept-org-head");
  const topBlock = node.locator(".dept-org-node-top");
  const metrics = node.locator(".dept-org-metrics");

  await expect(node).toBeVisible();
  await expect(avatar).toBeVisible();

  const nodeStyle = await node.evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      gap: Number.parseFloat(style.gap),
      paddingTop: Number.parseFloat(style.paddingTop),
    };
  });
  const avatarBox = await avatar.boundingBox();
  const headStyle = await headBlock.evaluate((element) => {
    const style = window.getComputedStyle(element);
    return Number.parseFloat(style.gap);
  });
  const topStyle = await topBlock.evaluate((element) => {
    const style = window.getComputedStyle(element);
    return Number.parseFloat(style.gap);
  });
  const metricsStyle = await metrics.evaluate((element) => {
    const style = window.getComputedStyle(element);
    return Number.parseFloat(style.paddingTop);
  });

  expect(nodeStyle.gap).toBeLessThanOrEqual(9);
  expect(nodeStyle.paddingTop).toBeLessThanOrEqual(15);
  expect(headStyle).toBeLessThanOrEqual(5);
  expect(topStyle).toBeLessThanOrEqual(5);
  expect(metricsStyle).toBeLessThanOrEqual(9);
  expect(avatarBox?.width ?? 0).toBeGreaterThanOrEqual(58);
  expect(avatarBox?.height ?? 0).toBeGreaterThanOrEqual(58);
});
