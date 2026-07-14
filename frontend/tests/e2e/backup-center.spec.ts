import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";

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

type BackupSnapshotSummary = BackupSnapshot & {
  artifact_bucket: string;
  artifact_size_bytes: number;
  object_count: number | null;
  created_at: string;
  finished_at: string;
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

async function visibleBox(locator: Locator) {
  const box = await locator.boundingBox();
  expect(box).not.toBeNull();
  return box!;
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

test("latest backup job summary shows status color", async ({ page }) => {
  const fakeOverview = {
    config_count: 2,
    configs: [
      {
        id: 1,
        kind: "db",
        kind_label: "Cơ sở dữ liệu PostgreSQL",
        enabled: true,
        cron_expression: "0 2 * * *",
        retention_days: 90,
        source_endpoint: null,
        source_bucket: null,
        source_secure: null,
        target_endpoint: "minio:9000",
        target_bucket: "hrms-backup",
        target_prefix: "postgres",
        target_secure: false,
        notify_emails: null,
        secret_source: "env",
        source_configured: true,
        target_configured: true,
        last_validated_at: "2026-07-14T01:00:00+07:00",
        last_validation_status: "success",
        last_validation_error: null,
        created_at: "2026-07-14T01:00:00+07:00",
        updated_at: "2026-07-14T01:00:00+07:00",
      },
      {
        id: 2,
        kind: "object_storage",
        kind_label: "Tệp tải lên trên MinIO",
        enabled: true,
        cron_expression: "0 3 * * *",
        retention_days: 90,
        source_endpoint: "minio:9000",
        source_bucket: "hrms-attachments-dev",
        source_secure: false,
        target_endpoint: "minio:9000",
        target_bucket: "hrms-backup",
        target_prefix: "files",
        target_secure: false,
        notify_emails: null,
        secret_source: "env",
        source_configured: true,
        target_configured: true,
        last_validated_at: null,
        last_validation_status: null,
        last_validation_error: null,
        created_at: "2026-07-14T01:00:00+07:00",
        updated_at: "2026-07-14T01:00:00+07:00",
      },
    ],
    latest_jobs: [
      {
        id: 501,
        kind: "db",
        trigger: "manual",
        status: "failed",
        artifact_key: null,
        artifact_bucket: null,
        artifact_size_bytes: null,
        object_count: null,
        started_at: "2026-07-14T01:01:00+07:00",
        finished_at: "2026-07-14T01:02:00+07:00",
        error_summary: "Không kết nối được đích sao lưu",
        log_excerpt: null,
        created_at: "2026-07-14T01:01:00+07:00",
      },
    ],
    latest_restore_requests: [],
  };

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.route("**/api/v1/backups/overview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fakeOverview),
    });
  });
  await page.route("**/api/v1/backups/snapshots**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "[]",
    });
  });

  await openBackupCenter(page);

  const latestStatus = page.getByTestId("latest-job-status");
  await expect(latestStatus).toHaveText("Thất bại");
  await expect(latestStatus).toHaveClass(/p-tag-danger/);
});

test("backup snapshots table uses the standard paginator", async ({ page }) => {
  const fakeSnapshots: BackupSnapshotSummary[] = Array.from({ length: 12 }, (_, index) => {
    const itemNumber = String(index + 1).padStart(2, "0");
    return {
      kind: index % 2 === 0 ? "db" : "object_storage",
      artifact_key: index % 2 === 0
        ? `postgres/e2e-snapshot-${itemNumber}.sql.gz`
        : `files/e2e-snapshot-${itemNumber}`,
      artifact_bucket: "hrms-backup",
      artifact_size_bytes: 2048 + index,
      object_count: index % 2 === 0 ? null : 2,
      created_at: `2026-07-13T08:${itemNumber}:00`,
      finished_at: `2026-07-13T08:${itemNumber}:30`,
    };
  });

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.route("**/api/v1/backups/snapshots**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fakeSnapshots),
    });
  });

  await openBackupCenter(page);

  const table = page.getByTestId("backup-snapshot-table");
  await expect(table.locator(".p-paginator")).toBeVisible();
  await expect(table.locator(".paginator-info")).toHaveText("Hiển thị 1–10 / 12");
  await expect(table).toContainText("postgres/e2e-snapshot-01.sql.gz");
  await expect(table).not.toContainText("postgres/e2e-snapshot-11.sql.gz");

  await table.locator(".p-paginator-next").click();

  await expect(table.locator(".paginator-info")).toHaveText("Hiển thị 11–12 / 12");
  await expect(table).toContainText("postgres/e2e-snapshot-11.sql.gz");
});

test("backup schedule time remains readable in dark mode", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("hrms-dark-mode", "true");
  });

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  await openBackupCenter(page);

  await expect(page.locator("html.dark-mode")).toHaveCount(1);
  const cronBadge = page.locator(".backup-code").filter({ hasText: "02:00" }).first();
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

test("backup config dialog remains usable on a narrow viewport", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await openBackupCenter(page);

  await page.getByRole("button", { name: "Sửa cấu hình sao lưu Cơ sở dữ liệu PostgreSQL" }).click();
  const dialog = page.getByRole("dialog", { name: "Sửa cấu hình sao lưu: Cơ sở dữ liệu PostgreSQL" });
  await expect(dialog).toBeVisible();

  await page.setViewportSize({ width: 390, height: 720 });
  await expect(dialog).toBeVisible();

  const enabledField = dialog.locator(".backup-field", { hasText: "Kích hoạt" }).first();
  const scheduleField = dialog.locator(".backup-field", { hasText: "Giờ chạy hằng ngày" }).first();
  const enabledBox = await visibleBox(enabledField);
  const scheduleBox = await visibleBox(scheduleField);
  const dialogBox = await visibleBox(dialog);

  expect(dialogBox.width).toBeLessThanOrEqual(390);
  expect(Math.abs(enabledBox.x - scheduleBox.x)).toBeLessThan(4);
  expect(scheduleBox.y).toBeGreaterThan(enabledBox.y + enabledBox.height - 1);

  const hasHorizontalOverflow = await dialog.evaluate((element) => element.scrollWidth > element.clientWidth + 1);
  expect(hasHorizontalOverflow).toBeFalsy();

  const cancelBox = await visibleBox(dialog.getByRole("button", { name: "Hủy" }));
  const saveBox = await visibleBox(dialog.getByRole("button", { name: "Lưu", exact: true }));
  expect(Math.abs(cancelBox.x - saveBox.x)).toBeLessThan(4);
  expect(cancelBox.width).toBeGreaterThan(300);
  expect(saveBox.width).toBeGreaterThan(300);
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

    await page.getByRole("button", { name: "Sửa cấu hình sao lưu Cơ sở dữ liệu PostgreSQL" }).click();
    const dialog = page.getByRole("dialog", { name: "Sửa cấu hình sao lưu: Cơ sở dữ liệu PostgreSQL" });
    await expect(dialog).toBeVisible();
    await expect(dialog).not.toContainText(ENGLISH_BACKUP_UI_PATTERN);
    await expect(dialog).not.toContainText(/\d+\s+\d+\s+\*\s+\*\s+\*/);
    await expect(dialog.getByLabel("Giờ chạy hằng ngày")).toHaveAttribute("type", "time");

    await page.getByLabel("Giờ chạy hằng ngày").fill("04:20");
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
    const savedConfig = await (await saveResponse).json();
    expect(savedConfig.cron_expression).toBe("20 4 * * *");
    await expect(page.getByRole("dialog", { name: "Sửa cấu hình sao lưu: Cơ sở dữ liệu PostgreSQL" })).toHaveCount(0);

    await page.getByRole("link", { name: /Dashboard tổng quan/ }).first().click();
    await expect(page).toHaveURL(/\/reports\/dashboard$/);
    await openBackupCenter(page);

    await expect(page.getByTestId("backup-config-table")).toContainText(`Giữ ${nextRetentionDays} ngày`);
    await expect(page.getByTestId("backup-config-table")).toContainText("04:20");
    await expect(page.getByTestId("backup-config-table")).not.toContainText("20 4 * * *");
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
