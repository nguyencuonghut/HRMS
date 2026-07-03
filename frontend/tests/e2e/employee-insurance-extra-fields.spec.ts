import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

type InsuranceListItem = {
  employee_id: number;
  employee_code: string;
  employee_name: string;
};

type InsuranceProfile = {
  employee_id: number;
  bhxh_code: string | null;
  health_care_insurance_code: string | null;
  health_care_family_participation: boolean | null;
  accident_insurance_code: string | null;
  bhyt_initial_clinic_name: string | null;
  bhyt_initial_clinic_code: string | null;
  company_bhxh_joined_date: string | null;
  participation_status: "active" | "paused" | "stopped";
  status_effective_from: string | null;
  status_note: string | null;
  insurance_basis_source: "contract" | "computed" | "manual_fixed";
  insurance_basis_amount: string | number | null;
  component_overrides?: unknown[];
};

async function login(page: Page, redirect = "/insurance") {
  await page.goto(`/login?redirect=${encodeURIComponent(redirect)}`);
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(new RegExp(redirect.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
}

async function adminToken(request: APIRequestContext) {
  const response = await request.post("/api/v1/auth/login", {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  expect(response.status()).toBe(200);
  const body = await response.json();
  return body.access_token as string;
}

function buildRestorePayload(profile: InsuranceProfile) {
  return {
    bhxh_code: profile.bhxh_code,
    health_care_insurance_code: profile.health_care_insurance_code,
    health_care_family_participation: profile.health_care_family_participation,
    accident_insurance_code: profile.accident_insurance_code,
    bhyt_initial_clinic_name: profile.bhyt_initial_clinic_name,
    bhyt_initial_clinic_code: profile.bhyt_initial_clinic_code,
    company_bhxh_joined_date: profile.company_bhxh_joined_date,
    participation_status: profile.participation_status,
    status_effective_from: profile.status_effective_from,
    status_note: profile.status_note,
    insurance_basis_source: profile.insurance_basis_source,
    insurance_basis_amount: profile.insurance_basis_amount,
    component_overrides: profile.component_overrides ?? [],
  };
}

test("insurance UI round-trips health care and accident insurance fields", async ({ page, request }) => {
  const token = await adminToken(request);
  const listResp = await request.get("/api/v1/insurance/employees?page=1&page_size=20", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(listResp.status()).toBe(200);
  const listBody = await listResp.json();
  const target = (listBody.items as InsuranceListItem[])[0];
  expect(target).toBeTruthy();

  const detailResp = await request.get(`/api/v1/insurance/employees/${target.employee_id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(detailResp.status()).toBe(200);
  const originalProfile = (await detailResp.json()) as InsuranceProfile;

  const stamp = String(Date.now()).slice(-6);
  const healthCode = `CSSK-${stamp}`;
  const accidentCode = `TAINAN-${stamp}`;

  try {
    await login(page, "/insurance");
    await page.waitForLoadState("networkidle");

    const row = page.locator("tbody tr").filter({ hasText: target.employee_code }).first();
    await expect(row).toBeVisible();
    await row.getByRole("button").click();

    const dialog = page.getByRole("dialog", { name: new RegExp(`Hồ sơ BHXH\\s+—\\s+${target.employee_name}`) });
    await expect(dialog).toBeVisible();

    const csskInput = dialog.locator(".field").filter({ hasText: /^Mã BH chăm sóc sức khỏe/ }).locator("input");
    const taiNanInput = dialog.locator(".field").filter({ hasText: /^Mã BH tai nạn/ }).locator("input");
    const familyCheckbox = dialog.getByLabel("Người thân tham gia cùng");

    await csskInput.fill(healthCode);
    await taiNanInput.fill(accidentCode);
    await familyCheckbox.check();

    const saveResp = page.waitForResponse((response) =>
      response.url().includes(`/api/v1/insurance/employees/${target.employee_id}`) &&
      response.request().method() === "PUT",
    );
    await dialog.getByRole("button", { name: "Lưu" }).click();
    expect((await saveResp).status()).toBe(200);
    await expect(dialog).toBeHidden();

    await expect(row.getByText(healthCode)).toBeVisible();
    await expect(row.getByText("Có")).toBeVisible();
    await expect(row.getByText(accidentCode)).toBeVisible();

    await page.goto(`/employees/${target.employee_id}`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("tab", { name: "Bảo hiểm" }).click();

    await expect(page.getByText("Mã BH chăm sóc sức khỏe")).toBeVisible();
    await expect(page.getByText(healthCode)).toBeVisible();
    await expect(page.getByText("Người thân tham gia CSSK")).toBeVisible();
    await expect(page.getByText(accidentCode)).toBeVisible();
  } finally {
    const restoreResp = await request.put(`/api/v1/insurance/employees/${target.employee_id}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: buildRestorePayload(originalProfile),
    });
    expect(restoreResp.status()).toBe(200);
  }
});
