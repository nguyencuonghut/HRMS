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

async function openTemplatesTab(page: Page) {
  await page.goto("/catalog/other-business");
  await page.getByRole("tab", { name: "Mẫu hợp đồng" }).click();
}

function placeholderDialog(page: Page): Locator {
  return page.locator(".p-dialog").filter({ hasText: "Placeholder của mẫu hợp đồng" });
}

async function createTemplateWithDocx(page: Page, code: string, name: string) {
  await page.getByRole("button", { name: "Thêm mẫu hợp đồng" }).click();

  const dialog = page.locator(".p-dialog").filter({ hasText: "Thêm mẫu hợp đồng" });
  await dialog.locator(".field").filter({ hasText: /^Mã/ }).locator("input").first().fill(code);
  await dialog.locator(".field").filter({ hasText: /^Tên mẫu/ }).locator("input").first().fill(name);
  await dialog.locator(".p-select").first().click();
  await page.locator(".p-select-option").first().click();
  await dialog.locator('input[type="file"]').first().setInputFiles("tests/fixtures/sample-template.docx");

  const createResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates") &&
      response.request().method() === "POST" &&
      !response.url().includes("/upload");
  });
  await dialog.getByRole("button", { name: "Tạo mới" }).click();
  expect((await createResponsePromise).status()).toBe(201);

  const uploadResponse = await page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates/") &&
      response.url().includes("/upload") &&
      response.request().method() === "POST";
  });
  expect(uploadResponse.status()).toBe(200);
}

test("placeholder dialog lets users choose a registry field instead of typing source_path manually", async ({ page }) => {
  await page.setViewportSize({ width: 1680, height: 1200 });
  const unique = Date.now().toString();
  const code = `E2E_TEMPLATE_PH_${unique}`;
  const name = `E2E Template Placeholder ${unique}`;

  await login(page);
  await openTemplatesTab(page);
  await createTemplateWithDocx(page, code, name);

  const row = page.locator("tr").filter({ hasText: name }).first();
  await expect(row).toBeVisible();
  await row.getByLabel("Quản lý placeholder").click();

  const phDialog = placeholderDialog(page);
  await expect(phDialog.getByText("Chọn trường dữ liệu nghiệp vụ")).toBeVisible();
  const dialogBox = await phDialog.boundingBox();
  expect(dialogBox?.width ?? 0).toBeGreaterThan(1200);
  await phDialog.getByRole("button", { name: "Thêm placeholder" }).click();

  const firstRow = phDialog.locator(".p-datatable-tbody tr").first();
  await firstRow.locator(".p-select").first().click();
  await page.getByRole("option", { name: "Địa chỉ thường trú (employee_address)" }).click();

  const textInputs = firstRow.locator("input");
  await expect(textInputs.nth(0)).toHaveValue("employee_address");
  await expect(textInputs.nth(1)).toHaveValue("Địa chỉ thường trú");
  await expect(textInputs.nth(2)).toHaveValue("Nhân viên");
  await expect(textInputs.nth(3)).toHaveValue("employee.permanent_address_full");
  await expect(textInputs.nth(4)).toHaveValue("Văn bản");
  await expect(firstRow.getByText("employee_addresses.full_address_text (address_type=permanent)")).toBeVisible();

  const saveResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates/") &&
      response.url().includes("/placeholders") &&
      response.request().method() === "PUT";
  });
  await phDialog.getByRole("button", { name: "Lưu placeholder" }).click();
  expect((await saveResponsePromise).status()).toBe(200);
  await expect(page.getByText("Đã lưu placeholder")).toBeVisible();

  await row.getByLabel("Quản lý placeholder").click();
  const reopenedDialog = placeholderDialog(page);
  const reopenedRow = reopenedDialog.locator(".p-datatable-tbody tr").first();
  const reopenedInputs = reopenedRow.locator("input");
  await expect(reopenedInputs.nth(0)).toHaveValue("employee_address");
  await expect(reopenedInputs.nth(3)).toHaveValue("employee.permanent_address_full");
  await expect(reopenedRow.getByText("employee_addresses.full_address_text (address_type=permanent)")).toBeVisible();
});

test("health warning clears after saving placeholders without reloading the page", async ({ page }) => {
  await page.setViewportSize({ width: 1680, height: 1200 });
  const unique = Date.now().toString();
  const code = `E2E_TEMPLATE_HEALTH_${unique}`;
  const name = `E2E Template Health ${unique}`;

  await login(page);
  await openTemplatesTab(page);
  await createTemplateWithDocx(page, code, name);

  const healthItem = page.locator(".health-item").filter({ hasText: name }).first();
  await expect(healthItem).toBeVisible();
  await expect(healthItem.getByText("Mẫu chưa có placeholder nào được khai báo")).toBeVisible();

  const row = page.locator("tr").filter({ hasText: name }).first();
  await row.getByLabel("Quản lý placeholder").click();

  const phDialog = placeholderDialog(page);
  await phDialog.getByRole("button", { name: "Thêm placeholder" }).click();
  const firstRow = phDialog.locator(".p-datatable-tbody tr").first();
  await firstRow.locator(".p-select").first().click();
  await page.getByRole("option", { name: "Họ và tên (employee_full_name)" }).click();

  const saveResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates/") &&
      response.url().includes("/placeholders") &&
      response.request().method() === "PUT";
  });
  await phDialog.getByRole("button", { name: "Lưu placeholder" }).click();
  expect((await saveResponsePromise).status()).toBe(200);
  await expect(page.getByText("Đã lưu placeholder")).toBeVisible();
  await expect(healthItem).toBeHidden();
});

test("inspect docx summary states detected vs auto-mapped placeholder counts", async ({ page }) => {
  await page.setViewportSize({ width: 1680, height: 1200 });
  await login(page);
  await openTemplatesTab(page);

  const row = page.locator("tr").filter({ hasText: "ld_definite_12m" }).first();
  await expect(row).toBeVisible();
  await row.getByLabel("Quản lý placeholder").click();

  const phDialog = placeholderDialog(page);
  const inspectResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/inspect-docx") && response.request().method() === "POST";
  });
  await phDialog.getByRole("button", { name: "Quét từ DOCX" }).click();
  const inspectResponse = await inspectResponsePromise;
  expect(inspectResponse.status()).toBe(200);
  const body = await inspectResponse.json();
  const detectedCount = body.detected_placeholders.length;
  const mappedCount = body.suggested_rows.length;
  const unsupportedCount = body.unsupported_count;

  await expect(phDialog.getByText(`${mappedCount}/${detectedCount} placeholder đã auto-map vào bảng bên dưới`)).toBeVisible();
  await expect(phDialog.getByText(`${detectedCount} placeholder phát hiện trong file`)).toBeVisible();
  await expect(phDialog.getByText(`${mappedCount} placeholder có thể map tự động`)).toBeVisible();
  await expect(phDialog.getByText(`${unsupportedCount} placeholder cần xử lý tay`)).toBeVisible();
});
