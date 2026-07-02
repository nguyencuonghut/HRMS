import { expect, test, type Locator, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page, redirect = "/reports/dashboard") {
  await page.goto(`/login?redirect=${encodeURIComponent(redirect)}`);
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|reports\/dashboard|reports\/training|reports\/export)/);
}

async function expectCardInset(card: Locator, innerSelector: string, expectedPadding = 14) {
  const metrics = await card.evaluate((element, selector) => {
    const inner = element.querySelector(selector);
    if (!inner) {
      return null;
    }
    const cardRect = element.getBoundingClientRect();
    const innerRect = inner.getBoundingClientRect();
    const style = window.getComputedStyle(element as HTMLElement);
    return {
      paddingTop: style.paddingTop,
      paddingRight: style.paddingRight,
      paddingBottom: style.paddingBottom,
      paddingLeft: style.paddingLeft,
      insetTop: Math.round(innerRect.top - cardRect.top),
      insetLeft: Math.round(innerRect.left - cardRect.left),
    };
  }, innerSelector);

  expect(metrics).not.toBeNull();
  expect(metrics?.paddingTop).toBe(`${expectedPadding}px`);
  expect(metrics?.paddingRight).toBe(`${expectedPadding}px`);
  expect(metrics?.paddingBottom).toBe(`${expectedPadding}px`);
  expect(metrics?.paddingLeft).toBe(`${expectedPadding}px`);
  expect(metrics?.insetTop ?? 0).toBeGreaterThanOrEqual(expectedPadding);
  expect(metrics?.insetLeft ?? 0).toBeGreaterThanOrEqual(expectedPadding);
}

test.describe("Card spacing regression", () => {
  test("training report cards keep a consistent inset from card edges", async ({ page }) => {
    await login(page, "/reports/training");
    await page.goto("/reports/training");
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: "Xem báo cáo" }).click();
    await page.waitForLoadState("networkidle");

    const courseCard = page.locator(".training-report-section-title", { hasText: "Theo khóa học" }).locator("..");
    const departmentCard = page.locator(".training-report-section-title", { hasText: "Theo phòng ban" }).locator("..");
    const incompleteCard = page.locator(".training-report-section-title", { hasText: "Nhân viên chưa hoàn thành đào tạo bắt buộc" }).locator("..").locator("..");

    await expectCardInset(courseCard, ".training-report-section-title");
    await expectCardInset(departmentCard, ".training-report-section-title");
    await expectCardInset(incompleteCard, ".training-report-section-title");
  });

  test("export center cards use the same card padding token", async ({ page }) => {
    await login(page, "/reports/export");
    await page.goto("/reports/export");
    await page.waitForLoadState("networkidle");

    await expectCardInset(page.locator(".export-main-card"), ".export-section-header");
    await expectCardInset(page.locator(".export-side-card"), ".export-section-header");

    await page.getByRole("tab", { name: "Lịch sử" }).click();
    await page.waitForLoadState("networkidle");
    await expectCardInset(page.locator(".export-history-card"), ".export-section-header");

    await page.getByRole("tab", { name: "Mẫu", exact: true }).click();
    await page.waitForLoadState("networkidle");
    await expectCardInset(page.locator(".export-template-card"), ".export-section-header");

    await page.getByRole("tab", { name: "Biểu mẫu BHXH" }).click();
    await page.waitForLoadState("networkidle");
    await expectCardInset(page.locator(".bhxh-filter-card"), ".bhxh-filter-row");
    await expectCardInset(page.locator(".bhxh-form-card").first(), ".bhxh-form-info");
  });
});
