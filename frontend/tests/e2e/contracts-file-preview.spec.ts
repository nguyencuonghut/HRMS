import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(/\/(dashboard|contracts)/);
}

test.describe("Hợp đồng - preview file", () => {
  test("opens preview for pdf/image file and keeps non-previewable file as static icon", async ({ page }) => {
    await page.addInitScript(() => {
      const originalOpen = window.open.bind(window);
      ;(window as typeof window & { __openedUrls?: string[] }).__openedUrls = [];
      window.open = ((url?: string | URL, target?: string, features?: string) => {
        const href = typeof url === "string" ? url : url?.toString() ?? "";
        ;(window as typeof window & { __openedUrls?: string[] }).__openedUrls?.push(href);
        return originalOpen(url, target, features);
      }) as typeof window.open;
    });

    await login(page);

    await page.route("**/api/v1/contracts**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: 101,
              employee_id: 11,
              parent_contract_id: null,
              contract_category_id: 1,
              category_name: "Hợp đồng lao động",
              document_kind: "labor_contract",
              contract_number: "HD-101",
              signed_date: "2026-01-01",
              effective_from: "2026-01-01",
              effective_to: null,
              insurance_salary: null,
              insurance_salary_mode: "fixed_manual",
              bhxh_position_group_id: null,
              bhxh_position_group_code: null,
              bhxh_position_group_name: null,
              insurance_salary_grade_no: null,
              resolved_insurance_salary_grade_no: null,
              bhxh_seniority_start_date: null,
              insurance_salary_fixed_amount: null,
              status: "active",
              status_display: "Đang hiệu lực",
              days_until_expiry: null,
              has_file: true,
              file_name: "hop_dong_scan.pdf",
              file_size: 12345,
              mime_type: "application/pdf",
              notes: null,
              created_at: "2026-01-01T00:00:00",
              updated_at: null,
              appendices: [],
              employee_name: "Nguyễn Văn A",
              employee_code: "HC0001",
            },
            {
              id: 102,
              employee_id: 12,
              parent_contract_id: null,
              contract_category_id: 1,
              category_name: "Hợp đồng lao động",
              document_kind: "labor_contract",
              contract_number: "HD-102",
              signed_date: "2026-01-01",
              effective_from: "2026-01-01",
              effective_to: null,
              insurance_salary: null,
              insurance_salary_mode: "fixed_manual",
              bhxh_position_group_id: null,
              bhxh_position_group_code: null,
              bhxh_position_group_name: null,
              insurance_salary_grade_no: null,
              resolved_insurance_salary_grade_no: null,
              bhxh_seniority_start_date: null,
              insurance_salary_fixed_amount: null,
              status: "active",
              status_display: "Đang hiệu lực",
              days_until_expiry: null,
              has_file: true,
              file_name: "hop_dong_goc.docx",
              file_size: 22222,
              mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              notes: null,
              created_at: "2026-01-01T00:00:00",
              updated_at: null,
              appendices: [],
              employee_name: "Nguyễn Văn B",
              employee_code: "HC0002",
            },
          ],
          total: 2,
          page: 1,
          page_size: 25,
        }),
      });
    });

    let previewUrlCalls = 0;
    await page.route("**/api/v1/employees/11/contracts/101/preview-url", async (route) => {
      previewUrlCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          url: "/api/v1/employees/11/contracts/101/preview?token=preview-contract-token",
          expires_in_seconds: 300,
        }),
      });
    });
    await page.route("**/api/v1/employees/11/contracts/101/preview?token=preview-contract-token", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: {
          "Content-Disposition": 'inline; filename="hop_dong_scan.pdf"',
        },
        body: "%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n",
      });
    });

    await page.goto("/contracts");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Hợp đồng lao động" })).toBeVisible();

    const previewButtons = page.locator(".contract-file-button");
    await expect(previewButtons).toHaveCount(1);

    const staticPaperclips = page.locator('i.pi-paperclip').filter({ hasNot: page.locator(".contract-file-button") });
    await expect(staticPaperclips).toHaveCount(1);

    await previewButtons.first().click();

    await expect.poll(() => previewUrlCalls).toBe(1);
    await expect.poll(async () => {
      return await page.evaluate(() => {
        const urls = (window as typeof window & { __openedUrls?: string[] }).__openedUrls ?? [];
        return urls.some((value) =>
          value.includes("/api/v1/employees/11/contracts/101/preview?token=preview-contract-token"),
        );
      });
    }).toBe(true);
    await expect(page.getByText("Không xem được file hợp đồng")).toHaveCount(0);
  });
});
