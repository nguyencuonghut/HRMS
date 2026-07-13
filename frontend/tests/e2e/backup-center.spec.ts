import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";
const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";

async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByPlaceholder("Nhập mật khẩu").fill(password);

  const meResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/auth/me") && response.status() === 200
  ));

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await meResponse;
  await page.waitForLoadState("networkidle");
}

test("admin can open read-only backup center and see backend overview", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  const overviewResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/backups/overview") && response.status() === 200
  ));
  await page.goto("/admin/backups");
  const overview = await (await overviewResponse).json();
  await page.waitForLoadState("networkidle");

  await expect(page).toHaveURL(/\/admin\/backups$/);
  await expect(page.getByRole("heading", { name: "Sao lưu & khôi phục" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Sao lưu & khôi phục/ })).toBeVisible();

  await expect(page.getByTestId("backup-config-count")).toContainText(String(overview.config_count));
  await expect(page.getByTestId("backup-config-table")).toContainText("Database PostgreSQL");
  await expect(page.getByTestId("backup-config-table")).toContainText("File upload / object storage");
  await expect(page.getByTestId("backup-config-table")).toContainText("hrms-backup");
  await expect(page.getByTestId("backup-config-table")).toContainText("Hằng ngày lúc 02:00");
  await expect(page.getByText(/access_key|secret_key|password/i)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Lịch backup gần nhất" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Yêu cầu khôi phục gần nhất" })).toBeVisible();
});

test("backup cron expression remains readable in dark mode", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("hrms-dark-mode", "true");
  });

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  const overviewResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/backups/overview") && response.status() === 200
  ));
  await page.goto("/admin/backups");
  await overviewResponse;
  await page.waitForLoadState("networkidle");

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

test("user without backups permission cannot see or open backup center", async ({ page }) => {
  await login(page, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

  await expect(page.getByRole("link", { name: /Sao lưu & khôi phục/ })).toHaveCount(0);
  await page.goto("/admin/backups");
  await page.waitForURL("**/forbidden");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
});
