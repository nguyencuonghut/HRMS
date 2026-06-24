import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports\/hr)/);
}

test.describe("Báo cáo nhân sự", () => {
  test("renders employee list, movement, and older-worker tabs", async ({ page }) => {
    await login(page);
    await page.goto("/reports/hr");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: "Báo cáo nhân sự" }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Danh sách nhân viên" }),
    ).toBeVisible();
    const employeePanel = page.getByRole("tabpanel").filter({
      has: page.getByText("Tổng nhân sự"),
    });
    await expect(employeePanel.locator(".hr-table-card").first()).toBeVisible();
    await expect(employeePanel.locator("table").first()).toBeVisible();

    const tableRows = employeePanel.locator("tbody tr");
    expect(await tableRows.count()).toBeGreaterThan(0);

    const employeeListResponse = await page.request.get("/api/v1/reports/hr/employee-list?page=1&page_size=10");
    expect(employeeListResponse.ok()).toBeTruthy();
    const employeeListPayload = await employeeListResponse.json() as {
      items: Array<{ employee_code: string; full_name: string }>
    };
    expect(employeeListPayload.items.length).toBeGreaterThan(0);
    await expect(tableRows.first().getByRole("cell").first()).toHaveText(employeeListPayload.items[0].employee_code);

    await page.getByRole("tab", { name: "Biến động nhân sự" }).click();
    await page.waitForLoadState("networkidle");

    const movementPanel = page.getByRole("tabpanel").filter({
      has: page.getByText("Chuyển bộ phận"),
    });
    const summaryStrip = movementPanel.locator(".hr-summary-strip");
    await expect(summaryStrip).toContainText("Tuyển mới");
    await expect(summaryStrip).toContainText("Chuyển bộ phận");
    await expect(movementPanel.locator("tbody tr").first()).toBeVisible();

    await page.getByRole("tab", { name: "Người lao động cao tuổi" }).click();
    await page.waitForLoadState("networkidle");

    const olderWorkerPanel = page.getByRole("tabpanel").filter({
      has: page.getByText("Danh sách người lao động cao tuổi"),
    });
    await expect(olderWorkerPanel.getByText("Policy áp dụng")).toBeVisible();
    await expect(olderWorkerPanel.locator(".hr-table-card table").first()).toBeVisible();
  });

  test("opens mobile filter drawer on 375px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 900 });
    await login(page);
    await page.goto("/reports/hr");
    await page.waitForLoadState("networkidle");

    const filterButton = page.getByRole("button", { name: "Bộ lọc" });
    await expect(filterButton).toBeVisible();
    await filterButton.click();

    const drawer = page.getByRole("dialog");
    await expect(drawer.getByText("Bộ lọc báo cáo nhân sự")).toBeVisible();
    await expect(drawer.getByText("Phòng ban", { exact: true })).toBeVisible();
    await drawer.getByRole("button", { name: "Áp dụng" }).click();
    await expect(page.getByText("Bộ lọc báo cáo nhân sự")).toHaveCount(0);
  });
});
