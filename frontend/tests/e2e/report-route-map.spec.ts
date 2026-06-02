import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";
const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";

async function login(page: Page, email = ADMIN_EMAIL, password = ADMIN_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByPlaceholder("Nhập mật khẩu").fill(password);

  const loginMeResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await loginMeResponse;
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports)/);
}

async function navigate(page: Page, path: string) {
  await page.evaluate((nextPath) => {
    window.history.pushState({}, "", nextPath);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
}

test.describe.configure({ mode: "serial" });

test.describe("Report route map", () => {
  test("report hub exposes canonical report links", async ({ page }) => {
    await login(page);
    await navigate(page, "/reports");
    await page.waitForLoadState("networkidle");

    const main = page.locator("#main-content");
    await expect(main.getByRole("heading", { name: "Tổng quan báo cáo", exact: true })).toBeVisible();
    await expect(main.getByRole("link", { name: /Dashboard tổng quan/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Thử việc & onboarding/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo tuyển dụng/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo checklist hồ sơ lao động/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo đào tạo/i })).toBeVisible();
    await expect(main.getByRole("link", { name: /Báo cáo hiệu suất/i })).toBeVisible();
  });

  test("new canonical report routes render", async ({ page }) => {
    await login(page);
    const main = page.locator("#main-content");

    await navigate(page, "/reports/probation");
    await page.waitForLoadState("networkidle");
    await expect(main.locator(".ob-breadcrumb")).toContainText("Báo cáo");
    await expect(main.locator(".ob-breadcrumb")).toContainText("Báo cáo thử việc & onboarding");

    await navigate(page, "/reports/leave");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo nghỉ phép" })).toBeVisible();

    await navigate(page, "/reports/recruitment");
    await page.waitForLoadState("networkidle");
    await expect(main.locator(".rc-breadcrumb")).toContainText("Báo cáo");
    await expect(main.locator(".rc-jr-code")).toHaveText("Báo cáo tuyển dụng");

    await navigate(page, "/reports/employee-document-checklist");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo checklist hồ sơ lao động" })).toBeVisible();
    await expect(main.getByText("Theo dõi mức độ hoàn thành hồ sơ lao động bắt buộc", { exact: false })).toBeVisible();
    await expect(main.getByRole("columnheader", { name: "Thiếu giấy tờ gì" })).toBeVisible();

    await navigate(page, "/reports/training");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo đào tạo" })).toBeVisible();

    await navigate(page, "/reports/rewards");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo khen thưởng & kỷ luật" })).toBeVisible();

    await navigate(page, "/reports/performance");
    await page.waitForLoadState("networkidle");
    await expect(main.getByRole("heading", { name: "Báo cáo hiệu suất / KPI" })).toBeVisible();
  });

  test("employee document checklist report shows missing document names from summary response", async ({ page }) => {
    await login(page);

    const summaryResponsePromise = page.waitForResponse((response) =>
      response.url().includes("/api/v1/recruitment/document-checklist/summary") && response.status() === 200,
    );

    await navigate(page, "/reports/employee-document-checklist");
    await page.waitForLoadState("networkidle");

    const summaryResponse = await summaryResponsePromise;
    const summaryRows = (await summaryResponse.json()) as Array<{
      employee_code: string;
      missing_document_names: string[];
    }>;

    const main = page.locator("#main-content");
    await expect(main.getByRole("columnheader", { name: "Thiếu giấy tờ gì" })).toBeVisible();

    const incompleteRow = summaryRows.find((row) => row.missing_document_names.length > 0);
    if (incompleteRow) {
      const expectedText = incompleteRow.missing_document_names.join(", ");
      await expect(
        main.getByRole("cell", { name: incompleteRow.employee_code }).locator("xpath=ancestor::tr[1]"),
      ).toContainText(expectedText);
      return;
    }

    const missingColumnCells = main.locator("tbody tr td:nth-child(6)");
    await expect(missingColumnCells.first()).toHaveText("—");
  });

  test("legacy report routes redirect to canonical routes", async ({ page }) => {
    await login(page);

    await navigate(page, "/employees/probation-reports");
    await page.waitForURL("**/reports/probation");

    await navigate(page, "/leave-reports");
    await page.waitForURL("**/reports/leave");

    await navigate(page, "/reports/leave-analytics");
    await page.waitForURL("**/reports/leave");

    await navigate(page, "/recruitment/reports");
    await page.waitForURL("**/reports/recruitment");

    await navigate(page, "/recruitment/legal");
    await page.waitForURL("**/reports/employee-document-checklist");
  });

  test("module shortcuts replace internal report tabs", async ({ page }) => {
    await login(page);

    await navigate(page, "/rewards");
    await expect(page.getByRole("tab", { name: "Báo cáo" })).toHaveCount(0);
    await page.getByRole("button", { name: "Xem báo cáo khen thưởng & kỷ luật" }).click();
    await page.waitForURL("**/reports/rewards");
    await expect(page.locator("#main-content").getByRole("heading", { name: "Báo cáo khen thưởng & kỷ luật" })).toBeVisible();

    await navigate(page, "/training");
    await expect(page.getByRole("tab", { name: "Báo cáo" })).toHaveCount(0);
    await page.getByRole("button", { name: "Xem báo cáo đào tạo" }).click();
    await page.waitForURL("**/reports/training");
    await expect(page.locator("#main-content").getByRole("heading", { name: "Báo cáo đào tạo" })).toBeVisible();

    await navigate(page, "/performance");
    await expect(page.getByRole("tab", { name: "Báo cáo" })).toHaveCount(0);
    await page.getByRole("button", { name: "Xem báo cáo hiệu suất" }).click();
    await page.waitForURL("**/reports/performance");
    await expect(page.locator("#main-content").getByRole("heading", { name: "Báo cáo hiệu suất / KPI" })).toBeVisible();
  });

  test("report menu uses canonical labels", async ({ page }) => {
    await login(page);

    const nav = page.locator("nav");
    await expect(nav.locator('a[href="/reports"]')).toContainText("Tổng quan báo cáo");
    await expect(nav.locator('a[href="/reports/dashboard"]').last()).toContainText("Dashboard tổng quan");
    await expect(nav.locator('a[href="/reports/hr"]')).toContainText("Nhân sự");
    await expect(nav.locator('a[href="/reports/probation"]')).toContainText("Thử việc & onboarding");
    await expect(nav.locator('a[href="/reports/leave"]')).toContainText("Nghỉ phép");
    await expect(nav.locator('a[href="/reports/insurance"]')).toContainText("Bảo hiểm");
    await expect(nav.locator('a[href="/reports/contracts"]')).toContainText("Hợp đồng");
    await expect(nav.locator('a[href="/reports/recruitment"]')).toContainText("Tuyển dụng");
    await expect(nav.locator('a[href="/reports/employee-document-checklist"]').last()).toContainText("Checklist hồ sơ lao động");
    await expect(nav.locator('a[href="/reports/training"]')).toContainText("Đào tạo");
    await expect(nav.locator('a[href="/reports/rewards"]')).toContainText("Khen thưởng & Kỷ luật");
    await expect(nav.locator('a[href="/reports/performance"]')).toContainText("Hiệu suất / KPI");
  });

  test("employee document checklist report activates only canonical report menu item", async ({ page }) => {
    await login(page);
    await navigate(page, "/reports/employee-document-checklist");
    await page.waitForLoadState("networkidle");

    const nav = page.locator("nav");
    await expect(nav.locator('a[href="/reports/employee-document-checklist"]').last()).toHaveClass(/router-link-active/);
    await expect(nav.locator('a[href="/recruitment/legal"]')).not.toHaveClass(/router-link-active/);
  });

  test("permission guard blocks report routes without required permission", async ({ page }) => {
    await login(page, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

    await navigate(page, "/reports/insurance");
    await page.waitForURL("**/forbidden");
    await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
  });

  test("insurance canonical route uses normalized heading", async ({ page }) => {
    await login(page);
    await navigate(page, "/reports/insurance");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#main-content").getByRole("heading", { name: "Phân tích bảo hiểm" })).toBeVisible();
  });
});
