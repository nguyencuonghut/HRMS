import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard)/);
}

test("can create contract template and upload a docx file from the dialog", async ({ page }) => {
  const unique = Date.now().toString();
  const code = `E2E_TEMPLATE_${unique}`;
  const name = `E2E Template ${unique}`;

  await login(page);
  await page.goto("/catalog/other-business");

  await page.getByRole("tab", { name: "Mẫu hợp đồng" }).click();
  await page.getByRole("button", { name: "Thêm mẫu hợp đồng" }).click();

  const dialog = page.locator(".p-dialog").filter({ hasText: "Thêm mẫu hợp đồng" });
  await dialog.locator(".field").filter({ hasText: /^Mã/ }).locator("input").first().fill(code);
  await dialog.locator(".field").filter({ hasText: /^Tên mẫu/ }).locator("input").first().fill(name);

  await dialog.locator(".p-select").first().click();
  await page.locator(".p-select-option").first().click();

  const fileInput = dialog.locator('input[type="file"]').first();
  await fileInput.setInputFiles("tests/fixtures/sample-template.docx");

  await expect(dialog.getByText("Đã chọn: sample-template.docx")).toBeVisible();
  await expect(dialog.locator(".field").filter({ hasText: /^Tên file/ }).locator("input").first()).toHaveValue("sample-template.docx");

  const createResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates") && response.request().method() === "POST" && !response.url().includes("/upload");
  });

  await dialog.getByRole("button", { name: "Tạo mới" }).click();

  const createResponse = await createResponsePromise;
  const createBody = await createResponse.text();
  expect(createResponse.status(), `create template failed: ${createBody}`).toBe(201);

  const uploadResponse = await page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contract-templates/") && response.url().includes("/upload") && response.request().method() === "POST";
  });
  const uploadBody = await uploadResponse.text();
  expect(uploadResponse.status(), `upload template failed: ${uploadBody}`).toBe(200);

  await expect(page.getByText("Đã tạo dữ liệu mới")).toBeVisible();
  await expect(page.getByRole("cell", { name })).toBeVisible();

  const row = page.locator("tr").filter({ hasText: name }).first();
  await row.locator("button").nth(2).click();

  const editDialog = page.locator(".p-dialog").filter({ hasText: "Chỉnh sửa mẫu hợp đồng" });
  await expect(editDialog.locator(".field").filter({ hasText: /^Storage path/ }).locator("input").first()).not.toHaveValue("");
  await editDialog.getByRole("button", { name: "Hủy" }).click();
});
