import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|employees\/1)/);
}

test.describe("Employee document tabs vocabulary", () => {
  test("shows renamed tabs and updated catalog options", async ({ page }) => {
    await login(page);
    await page.goto("/employees/1");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("tab", { name: "Tệp đính kèm hồ sơ" }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Checklist hồ sơ pháp lý" }),
    ).toBeVisible();

    await page.getByRole("tab", { name: "Tệp đính kèm hồ sơ" }).click();
    await page.getByRole("button", { name: "Tải lên tài liệu" }).click();
    const uploadDialog = page.getByRole("dialog", { name: "Tải lên tài liệu" });
    await uploadDialog.getByRole("combobox").click();
    const overlay = page.locator(".p-select-overlay:visible").last();
    await expect(overlay.getByText("Ảnh thẻ", { exact: true })).toBeVisible();
    await expect(overlay.getByText("CCCD — Mặt trước", { exact: true })).toBeVisible();
    await expect(overlay.getByText("CCCD — Mặt sau", { exact: true })).toBeVisible();
    await expect(overlay.getByText("Hộ chiếu", { exact: true })).toBeVisible();
    await expect(overlay.getByText("Bằng cấp", { exact: true })).toBeVisible();
    await expect(overlay.getByText("Chứng chỉ", { exact: true })).toBeVisible();
    await expect(overlay.getByText("Sơ yếu lý lịch", { exact: true })).toBeVisible();
    await expect(overlay.getByText("Giấy phép lao động (legacy)", { exact: true })).toHaveCount(0);
    await page.keyboard.press("Escape");
    await uploadDialog.getByRole("button", { name: "Hủy" }).click();

    await page.getByRole("tab", { name: "Checklist hồ sơ pháp lý" }).click();
    const legalPanel = page.getByRole("tabpanel", { name: "Checklist hồ sơ pháp lý" });
    await expect(legalPanel.getByText("Sơ yếu lý lịch", { exact: true })).toBeVisible();
    await expect(legalPanel.getByText("Xác nhận cư trú", { exact: true })).toBeVisible();
    await expect(legalPanel.getByText("Đơn xin việc", { exact: true })).toBeVisible();
  });

  test("allows previewing image/pdf files in both tabs", async ({ page }) => {
    await login(page);
    await page.goto("/employees/1");
    await page.waitForLoadState("networkidle");

    await page.getByRole("tab", { name: "Tệp đính kèm hồ sơ" }).click();
    await page.getByRole("button", { name: "Tải lên tài liệu" }).click();
    const uploadDialog = page.getByRole("dialog", { name: "Tải lên tài liệu" });
    await uploadDialog.getByRole("combobox").click();
    await page.locator(".p-select-overlay:visible").last().getByText("Ảnh thẻ", { exact: true }).click();
    await uploadDialog.locator('input[type="file"]').setInputFiles({
      name: "preview-attachment.png",
      mimeType: "image/png",
      buffer: Buffer.from("iVBORw0KGgo=", "base64"),
    });
    await uploadDialog.getByRole("button", { name: "Tải lên" }).click();
    const attachmentRow = page.locator(".attachment-row", { hasText: "preview-attachment.png" }).first();
    await expect(attachmentRow).toBeVisible();
    const attachmentPopup = page.waitForEvent("popup");
    await attachmentRow.getByRole("button", { name: "Xem file" }).click();
    const attachmentPreview = await attachmentPopup;
    await attachmentPreview.waitForLoadState("domcontentloaded");
    await expect(attachmentPreview).toHaveURL(/\/api\/v1\/employees\/1\/attachments\/\d+\/preview\?token=/);
    await expect(attachmentPreview.locator("img")).toBeVisible();
    await attachmentPreview.close();

    await page.getByRole("tab", { name: "Checklist hồ sơ pháp lý" }).click();
    const legalPanel = page.getByRole("tabpanel", { name: "Checklist hồ sơ pháp lý" });
    const legalRow = legalPanel.getByRole("row", { name: /Sơ yếu lý lịch/ });
    await legalRow.getByRole("button", { name: "Upload" }).click();
    await legalPanel.locator('input[type="file"]').setInputFiles({
      name: "preview-checklist.png",
      mimeType: "image/png",
      buffer: Buffer.from("iVBORw0KGgo=", "base64"),
    });
    await expect(legalRow.getByRole("button", { name: "Xem file" })).toBeVisible();
    const checklistPopup = page.waitForEvent("popup");
    await legalRow.getByRole("button", { name: "Xem file" }).click();
    const checklistPreview = await checklistPopup;
    await checklistPreview.waitForLoadState("domcontentloaded");
    await expect(checklistPreview).toHaveURL(/\/api\/v1\/employees\/1\/document-checklist\/\d+\/preview\?token=/);
    await expect(checklistPreview.locator("img")).toBeVisible();
    await checklistPreview.close();
  });
});
