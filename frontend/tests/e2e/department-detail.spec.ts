import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test("department list navigates to detail page and renders summary/direct employees", async ({
  page,
}) => {
  let detailRequestCount = 0;

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

  await expect(page.getByRole("cell", { name: "KS001" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Nguyễn Văn Cường" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Giám đốc khối kiểm soát" })).toBeVisible();
  await expect(page.getByText("Chính thức")).toBeVisible();

  expect(detailRequestCount).toBe(1);
});
