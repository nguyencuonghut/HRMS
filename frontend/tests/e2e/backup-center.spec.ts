import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";
const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";
const ENGLISH_BACKUP_UI_PATTERN = /\b(Database|File upload|object storage|Secret|Validate|Endpoint|Bucket|Prefix|Artifact|Job|backend|server|cron|HTTPS)\b/i;

test.describe.configure({ mode: "serial" });

type BackupConfig = {
  enabled: boolean;
  cron_expression: string;
  retention_days: number;
  source_endpoint: string | null;
  source_bucket: string | null;
  source_secure: boolean | null;
  target_endpoint: string | null;
  target_bucket: string;
  target_prefix: string | null;
  target_secure: boolean;
  notify_emails: string[] | null;
  kind: string;
};

type BackupConfigUpdatePayload = Omit<BackupConfig, "kind">;

type BackupJob = {
  id: number;
  kind: string;
  status: string;
  artifact_key: string | null;
};

type BackupSnapshot = {
  kind: string;
  artifact_key: string;
};

type BackupOverview = {
  config_count: number;
};

async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByPlaceholder("Nhập mật khẩu").fill(password);

  const meResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/auth/me") && response.status() === 200
  ));

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await meResponse;
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports)/);
  await page.waitForLoadState("networkidle");
}

async function loginViaApi(request: APIRequestContext, email: string, password: string): Promise<string> {
  const response = await request.post("/api/v1/auth/login", {
    data: { email, password },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.access_token as string;
}

function payloadFromConfig(config: BackupConfig): BackupConfigUpdatePayload {
  return {
    enabled: config.enabled,
    cron_expression: config.cron_expression,
    retention_days: config.retention_days,
    source_endpoint: config.source_endpoint,
    source_bucket: config.source_bucket,
    source_secure: config.source_secure,
    target_endpoint: config.target_endpoint,
    target_bucket: config.target_bucket,
    target_prefix: config.target_prefix,
    target_secure: config.target_secure,
    notify_emails: config.notify_emails,
  };
}

async function dbBackupConfig(request: APIRequestContext, token: string): Promise<BackupConfig> {
  const response = await request.get("/api/v1/backups/config", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  const configs = await response.json() as BackupConfig[];
  return configs.find((item) => item.kind === "db")!;
}

async function updateDbBackupConfig(
  request: APIRequestContext,
  token: string,
  payload: BackupConfigUpdatePayload,
) {
  const response = await request.put("/api/v1/backups/config/db", {
    headers: { Authorization: `Bearer ${token}` },
    data: payload,
  });
  expect(response.ok()).toBeTruthy();
}

function jobStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: "Đang chờ",
    running: "Đang chạy",
    success: "Thành công",
    failed: "Thất bại",
    cancelled: "Đã hủy",
  };
  return labels[status] ?? "Trạng thái khác";
}

function restoreStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: "Bản nháp",
    queued: "Đang chờ",
    running: "Đang chạy",
    verified: "Đã kiểm tra",
    restored: "Đã khôi phục",
    failed: "Thất bại",
    cancelled: "Đã hủy",
  };
  return labels[status] ?? "Trạng thái khác";
}

async function latestDbSnapshot(request: APIRequestContext, token: string): Promise<BackupSnapshot | null> {
  const response = await request.get("/api/v1/backups/snapshots", {
    headers: { Authorization: `Bearer ${token}` },
    params: { kind: "db", limit: 1 },
  });
  expect(response.ok()).toBeTruthy();
  const snapshots = await response.json() as BackupSnapshot[];
  return snapshots[0] ?? null;
}

async function ensureDbSnapshot(request: APIRequestContext, token: string): Promise<BackupSnapshot> {
  const existing = await latestDbSnapshot(request, token);
  if (existing) return existing;

  const createResponse = await request.post("/api/v1/backups/jobs", {
    headers: { Authorization: `Bearer ${token}` },
    data: { kind: "db" },
  });
  expect(createResponse.ok()).toBeTruthy();
  const job = await createResponse.json() as BackupJob;

  const deadline = Date.now() + 90000;
  while (Date.now() < deadline) {
    const jobsResponse = await request.get("/api/v1/backups/jobs", {
      headers: { Authorization: `Bearer ${token}` },
      params: { limit: 20 },
    });
    expect(jobsResponse.ok()).toBeTruthy();
    const jobs = await jobsResponse.json() as BackupJob[];
    const current = jobs.find((item) => item.id === job.id);
    if (current?.status === "success" && current.artifact_key) {
      return { kind: "db", artifact_key: current.artifact_key };
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("Không tạo được bản sao cơ sở dữ liệu trong thời gian chờ");
}

async function openBackupCenter(page: Page): Promise<BackupOverview> {
  const overviewResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/backups/overview") && response.status() === 200
  ));
  await page.getByRole("link", { name: /Sao lưu & khôi phục/ }).click();
  const overview = await (await overviewResponse).json() as BackupOverview;
  await expect(page).toHaveURL(/\/admin\/backups$/);
  await expect(page.getByRole("heading", { name: "Sao lưu & khôi phục" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  return overview;
}

test("admin can open read-only backup center and see backend overview", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  const overview = await openBackupCenter(page);

  await expect(page).toHaveURL(/\/admin\/backups$/);
  await expect(page.getByRole("heading", { name: "Sao lưu & khôi phục" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Sao lưu & khôi phục/ })).toBeVisible();

  await expect(page.getByTestId("backup-config-count")).toContainText(String(overview.config_count));
  await expect(page.getByTestId("backup-config-table")).toContainText("Cơ sở dữ liệu PostgreSQL");
  await expect(page.getByTestId("backup-config-table")).toContainText("Tệp tải lên trên MinIO");
  await expect(page.getByTestId("backup-config-table")).toContainText("hrms-backup");
  await expect(page.getByTestId("backup-config-table")).toContainText("Hằng ngày lúc 02:00");
  await expect(page.getByText(/access_key|secret_key|password/i)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Lịch sao lưu gần nhất" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Yêu cầu khôi phục gần nhất" })).toBeVisible();
  await expect(page.locator(".backup-center")).not.toContainText(ENGLISH_BACKUP_UI_PATTERN);
});

test("backup cron expression remains readable in dark mode", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("hrms-dark-mode", "true");
  });

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  await openBackupCenter(page);

  await expect(page.locator("html.dark-mode")).toHaveCount(1);
  const cronBadge = page.locator(".backup-code").filter({ hasText: "0 2 * * *" }).first();
  await expect(cronBadge).toBeVisible();

  const contrastRatio = await cronBadge.evaluate((el) => {
    const parseRgb = (raw: string): [number, number, number] => {
      const parts = raw.match(/\d+(\.\d+)?/g)?.slice(0, 3).map(Number) ?? [0, 0, 0];
      return [parts[0], parts[1], parts[2]];
    };
    const relativeLuminance = ([r, g, b]: [number, number, number]) => {
      const convert = (channel: number) => {
        const value = channel / 255;
        return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * convert(r) + 0.7152 * convert(g) + 0.0722 * convert(b);
    };

    const styles = getComputedStyle(el);
    const foreground = relativeLuminance(parseRgb(styles.color));
    const background = relativeLuminance(parseRgb(styles.backgroundColor));
    const lighter = Math.max(foreground, background);
    const darker = Math.min(foreground, background);
    return (lighter + 0.05) / (darker + 0.05);
  });

  expect(contrastRatio).toBeGreaterThan(4.5);
});

test("admin can save backup config and see the new value after reopening the page", async ({ page, request }) => {
  const token = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const original = await dbBackupConfig(request, token);
  const originalPayload = payloadFromConfig(original);
  const nextRetentionDays = original.retention_days === 41 ? 42 : 41;
  const nextPrefix = `e2e-slice4-${Date.now().toString(36)}`;

  try {
    await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

    await openBackupCenter(page);

    await page.getByRole("button", { name: "Sửa cấu hình Cơ sở dữ liệu PostgreSQL" }).click();
    const dialog = page.getByRole("dialog", { name: "Sửa cấu hình Cơ sở dữ liệu PostgreSQL" });
    await expect(dialog).toBeVisible();
    await expect(dialog).not.toContainText(ENGLISH_BACKUP_UI_PATTERN);

    await page.getByLabel("Lịch chạy").fill("20 4 * * *");
    await page.locator("#backup-retention").fill(String(nextRetentionDays));
    await page.getByLabel("Kho lưu trữ đích").fill("hrms-backup");
    await page.getByLabel("Thư mục đích").fill(nextPrefix);
    await page.getByLabel("Thư điện tử nhận thông báo").fill("backup-admin@hrms.local");

    const saveResponse = page.waitForResponse((response) => (
      response.url().includes("/api/v1/backups/config/db")
      && response.request().method() === "PUT"
      && response.status() === 200
    ));
    await page.getByRole("button", { name: "Lưu", exact: true }).click();
    await saveResponse;
    await expect(page.getByRole("dialog", { name: "Sửa cấu hình Cơ sở dữ liệu PostgreSQL" })).toHaveCount(0);

    await page.getByRole("link", { name: /Dashboard tổng quan/ }).first().click();
    await expect(page).toHaveURL(/\/reports\/dashboard$/);
    await openBackupCenter(page);

    await expect(page.getByTestId("backup-config-table")).toContainText(`Giữ ${nextRetentionDays} ngày`);
    await expect(page.getByTestId("backup-config-table")).toContainText(nextPrefix);
  } finally {
    await updateDbBackupConfig(request, token, originalPayload);
  }
});

test("admin can trigger backup target validation state from the table", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  await openBackupCenter(page);

  const validationResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/backups/validate-target")
    && response.request().method() === "POST"
    && response.status() === 200
  ));
  await page.getByRole("button", { name: "Kiểm tra đích sao lưu Cơ sở dữ liệu PostgreSQL" }).click();
  const validation = await (await validationResponse).json();

  await expect(page.getByTestId("backup-config-table")).toContainText(
    validation.status === "success" ? "Thành công" : "Thất bại",
  );
});

test("admin can queue a manual backup job from the backup center", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  await openBackupCenter(page);

  const jobResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/backups/jobs")
    && response.request().method() === "POST"
    && response.status() === 201
  ));
  await page.getByRole("button", { name: "Chạy sao lưu Cơ sở dữ liệu PostgreSQL" }).click();
  const job = await (await jobResponse).json();

  const history = page.locator(".backup-history-grid").first();
  await expect(history).toContainText("Cơ sở dữ liệu PostgreSQL");
  await expect(history).toContainText("Thủ công");
  await expect(history).toContainText(jobStatusLabel(job.status));
  await expect(page.locator(".backup-center")).not.toContainText(ENGLISH_BACKUP_UI_PATTERN);
});

test("admin can create a safe restore verification request from a snapshot", async ({ page, request }) => {
  const token = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const snapshot = await ensureDbSnapshot(request, token);

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  await openBackupCenter(page);

  await expect(page.getByTestId("backup-snapshot-table")).toContainText(snapshot.artifact_key);

  await page.getByRole("button", { name: `Tạo yêu cầu khôi phục ${snapshot.artifact_key}` }).click();
  const dialog = page.getByRole("dialog", { name: "Tạo yêu cầu khôi phục" });
  await expect(dialog).toBeVisible();
  await expect(dialog).not.toContainText(ENGLISH_BACKUP_UI_PATTERN);
  await expect(dialog).toContainText(snapshot.artifact_key);

  await dialog.getByLabel("Nội dung xác nhận").fill("TOI XAC NHAN");

  const restoreResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/backups/restore-requests")
    && response.request().method() === "POST"
    && response.status() === 201
  ));
  await dialog.getByRole("button", { name: "Tạo yêu cầu", exact: true }).click();
  const restoreRequest = await (await restoreResponse).json();

  const history = page.locator(".backup-history-grid").first();
  await expect(history).toContainText("Chỉ kiểm tra");
  await expect(history).toContainText(restoreStatusLabel(restoreRequest.status));
  await expect(page.locator(".backup-center")).not.toContainText(ENGLISH_BACKUP_UI_PATTERN);
});

test("user without backups permission cannot see or open backup center", async ({ page }) => {
  await login(page, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

  await expect(page.getByRole("link", { name: /Sao lưu & khôi phục/ })).toHaveCount(0);
  await page.goto("/admin/backups");
  await page.waitForURL("**/forbidden");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
});
