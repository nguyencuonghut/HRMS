import { expect, test, type Locator, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);
}

async function openTemplateTab(page: Page) {
  await page.getByRole("link", { name: /Danh mục nghiệp vụ khác/ }).click();
  await page.waitForURL(/\/catalog\/other-business/);
  await page.getByRole("tab", { name: "Mẫu hợp đồng" }).click();
}

function templateToolbar(page: Page): Locator {
  return page.locator(".toolbar").filter({ has: page.getByPlaceholder("Tìm mẫu hợp đồng/phụ lục...") });
}

function confirmDialog(page: Page): Locator {
  return page.locator(".p-confirmdialog");
}

async function setTemplateStatusFilter(page: Page, optionLabel: string) {
  const toolbar = templateToolbar(page);
  await toolbar.locator(".p-select").nth(0).click();
  await page.getByRole("option", { name: optionLabel }).click();
}

test("superuser can lock, unlock, and hard-delete contract templates from the list", async ({ page }) => {
  const unique = Date.now().toString();
  const code = `E2E_TEMPLATE_ACT_${unique}`;
  const name = `E2E Template Actions ${unique}`;

  await login(page);
  await openTemplateTab(page);

  await page.getByRole("button", { name: "Thêm mẫu hợp đồng" }).click();
  const dialog = page.locator(".p-dialog").filter({ hasText: "Thêm mẫu hợp đồng" });
  await dialog.locator(".field").filter({ hasText: /^Mã/ }).locator("input").first().fill(code);
  await dialog.locator(".field").filter({ hasText: /^Tên mẫu/ }).locator("input").first().fill(name);
  await dialog.locator(".p-select").first().click();
  await page.locator(".p-select-option").first().click();

  const createResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates") &&
      response.request().method() === "POST" &&
      !response.url().includes("/upload");
  });
  await dialog.getByRole("button", { name: "Tạo mới" }).click();
  expect((await createResponse).status()).toBe(201);

  const row = page.locator("tr").filter({ hasText: name }).first();
  await expect(row).toBeVisible();
  await expect(row.getByLabel("Khóa mẫu hợp đồng")).toBeVisible();
  await expect(row.getByLabel("Xóa hẳn mẫu hợp đồng")).toBeVisible();

  const lockResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates/") &&
      response.request().method() === "PUT";
  });
  await row.getByLabel("Khóa mẫu hợp đồng").click();
  await confirmDialog(page).getByRole("button", { name: "Khóa", exact: true }).click();
  expect((await lockResponse).status()).toBe(200);
  await expect(row).not.toBeVisible();

  await setTemplateStatusFilter(page, "Đã khóa");
  const lockedRow = page.locator("tr").filter({ hasText: name }).first();
  await expect(lockedRow).toBeVisible();
  await expect(lockedRow.getByLabel("Mở khóa mẫu hợp đồng")).toBeVisible();

  const unlockResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates/") &&
      response.request().method() === "PUT";
  });
  await lockedRow.getByLabel("Mở khóa mẫu hợp đồng").click();
  await confirmDialog(page).getByRole("button", { name: "Mở khóa", exact: true }).click();
  expect((await unlockResponse).status()).toBe(200);
  await expect(lockedRow).not.toBeVisible();

  await setTemplateStatusFilter(page, "Tất cả trạng thái");
  const restoredRow = page.locator("tr").filter({ hasText: name }).first();
  await expect(restoredRow).toBeVisible();

  await restoredRow.getByLabel("Xóa hẳn mẫu hợp đồng").click();
  await expect(page.getByText("không thể hoàn tác", { exact: false })).toBeVisible();
  await expect(page.getByText("không thể generate lại", { exact: false })).toBeVisible();

  const hardDeleteResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates/") &&
      response.url().includes("/hard") &&
      response.request().method() === "DELETE";
  });
  await confirmDialog(page).getByRole("button", { name: "Xóa hẳn", exact: true }).click();
  expect((await hardDeleteResponse).status()).toBe(200);
  await expect(restoredRow).not.toBeVisible();
});
