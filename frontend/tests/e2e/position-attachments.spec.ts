import { createHash, randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

// Tab "Tài liệu đính kèm" trong hộp thoại "Chi tiết vị trí công việc" chạy với backend thật (không mock):
// cần tài khoản admin@hrms.local và ít nhất một vị trí công việc.
const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

test.describe.configure({ mode: "serial" });

type Uploaded = { id: number; bytes: Buffer };

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

async function positionIdByCode(request: APIRequestContext, token: string, code: string): Promise<number> {
  const response = await request.get("/api/v1/job-positions", {
    headers: { Authorization: `Bearer ${token}` },
    params: { page_size: 200 },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  const rows: Array<{ id: number; code: string }> = Array.isArray(body) ? body : body.items;
  const row = rows.find((r) => r.code === code);
  expect(row, `không thấy vị trí ${code}`).toBeTruthy();
  return row!.id;
}

async function upload(request: APIRequestContext, token: string, positionId: number, name: string, size: number): Promise<Uploaded> {
  const bytes = Buffer.concat([Buffer.from("%PDF-1.4\n"), randomBytes(size)]);
  const response = await request.post(`/api/v1/job-positions/${positionId}/attachments`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: { file: { name, mimeType: "application/pdf", buffer: bytes } },
  });
  expect(response.status()).toBe(201);
  return { id: (await response.json()).id as number, bytes };
}

async function deleteViaApi(request: APIRequestContext, token: string, positionId: number, attachmentId: number) {
  await request.delete(`/api/v1/job-positions/${positionId}/attachments/${attachmentId}`, { headers: { Authorization: `Bearer ${token}` } });
}

const sha256 = (data: Buffer) => createHash("sha256").update(data).digest("hex");

for (const [label, base, size] of [
  ["a plain name", "e2e-position-attachment.pdf", 4_096],
  ["a name with spaces and # % +", "Quy trình #1 100% + A.pdf", 90_000],
] as const) {
  test(`clicking an attachment's name downloads the file with its name and content (${label})`, async ({ page, request }, testInfo) => {
    const token = await apiToken(request);
    await login(page);
    await page.goto("/org/positions");
    await page.waitForLoadState("networkidle");

    const firstRow = page.locator("tbody tr").first();
    const code = (await firstRow.locator("td").first().innerText()).trim();
    const positionId = await positionIdByCode(request, token, code);
    const name = `${Date.now()}-${base}`;
    const file = await upload(request, token, positionId, name, size);
    try {
      await firstRow.locator("button:has(.pi-eye)").click();
      await page.getByRole("tab", { name: "Tài liệu đính kèm" }).click();
      const fileName = page.getByText(name, { exact: true });
      await expect(fileName).toBeVisible();

      const [download] = await Promise.all([page.waitForEvent("download", { timeout: 15_000 }), fileName.click()]);

      // Trước khi sửa: thẻ <a href target="_blank"> không gửi Authorization nên backend trả 401 và không có tệp nào được tải (LD-008).
      expect(await download.failure()).toBeNull();
      expect(download.suggestedFilename()).toBe(name);
      const saved = testInfo.outputPath("downloaded.pdf");
      await download.saveAs(saved);
      expect(sha256(readFileSync(saved))).toBe(sha256(file.bytes));
    } finally {
      await deleteViaApi(request, token, positionId, file.id);
    }
  });
}
