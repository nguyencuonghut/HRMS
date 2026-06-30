import { expect, test, type Locator, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|settings|reports\/export)/);
}

async function expectSelectOptions(trigger: Locator, labels: string[]) {
  await trigger.click();
  const overlay = trigger.page().locator(".p-select-overlay:visible").last();
  await expect(overlay).toBeVisible();
  for (const label of labels) {
    await expect(overlay.getByText(label, { exact: true })).toBeVisible();
  }
  await trigger.page().keyboard.press("Escape");
}

test("notification settings uses backend metadata for event/status options", async ({ page }) => {
  await login(page);

  const metaResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/api/v1/notifications/meta") &&
    response.request().method() === "GET" &&
    response.ok(),
  );

  await page.goto("/settings/notifications");
  await expect(page.getByRole("heading", { name: "Cài đặt thông báo" })).toBeVisible();
  const meta = await (await metaResponsePromise).json();

  expect(meta.event_types.some((item: { code: string }) => item.code === "certificate_expiry")).toBeFalsy();

  const eventLabels = meta.event_types.map((item: { label: string }) => item.label);
  const statusLabels = meta.statuses.map((item: { label: string }) => item.label);

  await page.getByRole("tab", { name: "Lịch sử gửi" }).click();
  const filters = page.locator(".notif-log-filters .p-select");
  await expect(filters).toHaveCount(2);

  await expectSelectOptions(filters.nth(0), eventLabels);
  await expectSelectOptions(filters.nth(1), statusLabels);
  await expect(page.locator(".notif-log-card")).not.toContainText("certificate_expiry");
});

test("export center uses backend metadata for report and format options", async ({ page }) => {
  await login(page);

  const metaResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/api/v1/reports/export/meta") &&
    response.request().method() === "GET" &&
    response.ok(),
  );

  await page.goto("/reports/export");
  await expect(page.getByRole("heading", { name: "Xuất báo cáo" })).toBeVisible();
  const meta = await (await metaResponsePromise).json();

  const reportLabels = meta.report_types.map((item: { label: string }) => item.label);
  const formatLabels = meta.formats.map((item: { label: string }) => item.label);

  const reportSelect = page.locator(".export-field", { hasText: "Loại báo cáo" }).locator(".p-select");
  const formatSelect = page.locator(".export-field", { hasText: "Định dạng" }).locator(".p-select");

  await expectSelectOptions(reportSelect, reportLabels);
  await expectSelectOptions(formatSelect, formatLabels);
});

test("audit log uses backend metadata for action and entity filters", async ({ page }) => {
  await login(page);

  const metaResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/api/v1/audit-logs/meta") &&
    response.request().method() === "GET" &&
    response.ok(),
  );
  const listResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/api/v1/audit-logs?") &&
    response.request().method() === "GET" &&
    response.ok(),
  );

  await page.goto("/admin/audit-logs");
  await expect(page.getByRole("heading", { name: "Nhật ký hệ thống" })).toBeVisible();
  const meta = await (await metaResponsePromise).json();
  const list = await (await listResponsePromise).json();

  const createContractAction = meta.actions.find((item: { code: string }) => item.code === "CREATE_CONTRACT");
  const leaveRecordEntity = meta.entity_types.find((item: { code: string }) => item.code === "leave_record");

  expect(createContractAction?.label).toBe("Tạo hợp đồng");
  expect(leaveRecordEntity?.label).toBe("Đơn nghỉ phép");

  if (list.items.length > 0) {
    expect(Object.prototype.hasOwnProperty.call(list.items[0], "action_label")).toBeTruthy();
    expect(Object.prototype.hasOwnProperty.call(list.items[0], "entity_type_label")).toBeTruthy();
  }

  const filters = page.locator(".toolbar .p-select");
  await expect(filters).toHaveCount(2);

  await expectSelectOptions(filters.nth(0), [createContractAction.label]);
  await expectSelectOptions(filters.nth(1), [leaveRecordEntity.label]);
});
