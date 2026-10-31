import { createHash, randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

// Tab "Tệp đính kèm hồ sơ" chạy với backend thật (không mock): cần tài khoản admin@hrms.local và ít nhất một nhân viên.
const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test.describe.configure({ mode: "serial" });

type Uploaded = { id: number; bytes: Buffer; name: string };

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  const me = page.waitForResponse((r) => r.url().includes("/api/v1/auth/me") && r.status() === 200);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await me;
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports)/);
}

async function apiToken(request: APIRequestContext): Promise<string> {
  const response = await request.post("/api/v1/auth/login", { data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD } });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).access_token as string;
}

async function firstEmployeeId(request: APIRequestContext, token: string): Promise<number> {
  const response = await request.get("/api/v1/employees?page=1&page_size=1", { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  const items = Array.isArray(body) ? body : body.items;
  expect(items.length).toBeGreaterThan(0);
  return items[0].id as number;
}

async function uploadPdf(request: APIRequestContext, token: string, employeeId: number, name: string, size: number): Promise<Uploaded> {
  const bytes = Buffer.concat([Buffer.from("%PDF-1.4\n"), randomBytes(size)]);
  const response = await request.post(`/api/v1/employees/${employeeId}/attachments`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      file: { name, mimeType: "application/pdf", buffer: bytes },
      document_type: "degree",
      description: "e2e employee-attachments",
    },
  });
  expect(response.status()).toBe(201);
  return { id: (await response.json()).id as number, bytes, name };
}

async function deleteViaApi(request: APIRequestContext, token: string, employeeId: number, attachmentId: number) {
  await request.delete(`/api/v1/employees/${employeeId}/attachments/${attachmentId}`, { headers: { Authorization: `Bearer ${token}` } });
}

async function openAttachmentsTab(page: Page, employeeId: number) {
  await page.goto(`/employees/${employeeId}`);
  // Chờ trang yên trước khi bấm tab: bấm khi hồ sơ còn đang tải thỉnh thoảng làm PrimeVue TabList báo lỗi (LD-005).
  await page.waitForLoadState("networkidle");
  await page.getByRole("tab", { name: "Tệp đính kèm hồ sơ" }).click();
}

const sha256 = (data: Buffer) => createHash("sha256").update(data).digest("hex");

test("deleting an attachment closes the confirmation dialog", async ({ page, request }) => {
  const token = await apiToken(request);
  const employeeId = await firstEmployeeId(request, token);
  const file = await uploadPdf(request, token, employeeId, `e2e-delete-${Date.now()}.pdf`, 2048);
  try {
    await login(page);
    await openAttachmentsTab(page, employeeId);
    const row = page.locator(".attachment-row").filter({ hasText: file.name });
    await expect(row).toHaveCount(1);

    await row.locator("button:has(.pi-trash)").click();
    const dialogs = page.locator(".p-confirmdialog:visible");
    await expect(dialogs.first()).toBeVisible();
    // Chờ hoạt ảnh mở hộp thoại xong để một hộp thoại thứ hai (nếu có) kịp hiện ra, rồi mới đếm.
    await page.waitForTimeout(500);
    // Trước khi sửa: hai ConfirmDialog cùng hiện cho một lần xóa, và hộp thoại còn lại không đóng (LD-001).
    await expect(dialogs).toHaveCount(1);
    await dialogs.getByRole("button", { name: "Xóa" }).click();

    await expect(row).toHaveCount(0);
    await expect(page.locator(".p-confirmdialog:visible")).toHaveCount(0);
  } finally {
    await deleteViaApi(request, token, employeeId, file.id);
  }
});

for (const [label, name, size] of [
  ["a name with spaces and # % +", "Bằng cấp #1 100% + A.pdf", 90_000],
  ["a file larger than 5 MiB", "e2e-large-attachment.pdf", 6 * 1024 * 1024],
] as const) {
  test(`downloading an attachment keeps its name and content (${label})`, async ({ page, request }, testInfo) => {
    const token = await apiToken(request);
    const employeeId = await firstEmployeeId(request, token);
    const file = await uploadPdf(request, token, employeeId, `${Date.now()}-${name}`, size);
    try {
      await login(page);
      await openAttachmentsTab(page, employeeId);
      const row = page.locator(".attachment-row").filter({ hasText: file.name });
      await expect(row).toHaveCount(1);

      const [download] = await Promise.all([
        page.waitForEvent("download"),
        row.locator("button:has(.pi-download)").click(),
      ]);

      // Trước khi sửa: thẻ <a href> không gửi Authorization nên backend trả 401 và tải bị hủy (LD-002).
      expect(await download.failure()).toBeNull();
      expect(download.suggestedFilename()).toBe(file.name);
      const saved = testInfo.outputPath("downloaded.pdf");
      await download.saveAs(saved);
      expect(sha256(readFileSync(saved))).toBe(sha256(file.bytes));
    } finally {
      await deleteViaApi(request, token, employeeId, file.id);
    }
  });
}
