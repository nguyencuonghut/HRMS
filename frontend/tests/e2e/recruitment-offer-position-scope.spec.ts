import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

type Department = {
  id: number;
  name: string;
  code: string;
};

type Position = {
  id: number;
  name: string;
  department_id: number;
};

type OfferFlowSeed = {
  applicationId: number;
  offerId: number;
  primaryDepartment: Department;
  secondaryDepartment: Department;
  primaryPosition: Position;
  secondaryPosition: Position;
};

async function login(page: Page, redirect: string) {
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

async function authHeaders(request: APIRequestContext) {
  const token = await adminToken(request);
  return { Authorization: `Bearer ${token}` };
}

async function apiGet<T>(request: APIRequestContext, url: string, headers: Record<string, string>, params?: Record<string, string | number | boolean>) {
  const response = await request.get(url, { headers, params });
  expect(response.status()).toBe(200);
  return await response.json() as T;
}

async function apiPost<T>(request: APIRequestContext, url: string, headers: Record<string, string>, data: unknown, expectedStatus = 201) {
  const response = await request.post(url, { headers, data });
  expect(response.status(), await response.text()).toBe(expectedStatus);
  return await response.json() as T;
}

async function apiPut<T>(request: APIRequestContext, url: string, headers: Record<string, string>, data: unknown) {
  const response = await request.put(url, { headers, data });
  expect(response.status(), await response.text()).toBe(200);
  return await response.json() as T;
}

async function getAnyJobTitleId(request: APIRequestContext, headers: Record<string, string>) {
  const rows = await apiGet<Array<{ id: number }>>(
    request,
    "/api/v1/job-titles",
    headers,
  );
  expect(rows.length).toBeGreaterThan(0);
  return rows[0].id;
}

async function createDepartment(
  request: APIRequestContext,
  headers: Record<string, string>,
  code: string,
  name: string,
) {
  return await apiPost<Department>(
    request,
    "/api/v1/departments",
    headers,
    { code, name, dept_type: "PHONG" },
  );
}

async function createPosition(
  request: APIRequestContext,
  headers: Record<string, string>,
  data: {
    code: string;
    name: string;
    department_id: number;
    job_title_id: number | null;
  },
) {
  return await apiPost<Position & { assigned_department_ids?: number[] }>(
    request,
    "/api/v1/job-positions",
    headers,
    data,
  );
}

async function createApprovedJr(
  request: APIRequestContext,
  headers: Record<string, string>,
  data: {
    positionId: number;
    departmentId: number;
  },
) {
  const jr = await apiPost<{ id: number }>(
    request,
    "/api/v1/recruitment/job-requisitions",
    headers,
    {
      job_position_id: data.positionId,
      department_id: data.departmentId,
      quantity: 1,
      reason_type: "new",
    },
  );
  await apiPost(
    request,
    `/api/v1/recruitment/job-requisitions/${jr.id}/submit`,
    headers,
    {},
    200,
  );
  await apiPost(
    request,
    `/api/v1/recruitment/job-requisitions/${jr.id}/approve`,
    headers,
    {},
    200,
  );
  await apiPost(
    request,
    `/api/v1/recruitment/job-requisitions/${jr.id}/pipeline`,
    headers,
    {
      stages: [
        {
          stage_order: 1,
          stage_name: "Sàng lọc hồ sơ",
          stage_type: "screening",
          is_active: true,
        },
      ],
    },
    200,
  );
  return jr.id;
}

async function createCandidate(request: APIRequestContext, headers: Record<string, string>, suffix: string) {
  const nationalities = await apiGet<Array<{ id: number; code: string }>>(
    request,
    "/api/v1/nationalities",
    headers,
  );
  const vn = nationalities.find((item) => item.code === "VN") ?? nationalities[0];
  expect(vn).toBeTruthy();
  return await apiPost<{ id: number }>(
    request,
    "/api/v1/recruitment/candidates",
    headers,
    {
      full_name: `Ứng viên Offer Scope ${suffix}`,
      last_name: "Ứng viên",
      first_name: `Scope ${suffix}`,
      personal_email: `offer_scope_${suffix}@example.com`,
      date_of_birth: "1990-01-01",
      gender: "male",
      nationality_id: vn.id,
      id_number: `ID${suffix.slice(0, 10)}`,
      id_issued_on: "2015-01-01",
      id_issued_by: "Cục CSQLHC",
    },
  );
}

async function applyAndAdvanceToOffer(
  request: APIRequestContext,
  headers: Record<string, string>,
  data: {
    candidateId: number;
    jrId: number;
  },
) {
  const application = await apiPost<{ id: number; current_stage: string }>(
    request,
    `/api/v1/recruitment/candidates/${data.candidateId}/apply`,
    headers,
    {
      job_requisition_id: data.jrId,
      applied_date: new Date().toISOString().slice(0, 10),
    },
  );

  const stages = await apiGet<Array<{ id: number; stage_type: string }>>(
    request,
    `/api/v1/recruitment/job-requisitions/${data.jrId}/pipeline`,
    headers,
  );
  expect(stages.length).toBeGreaterThan(0);

  let currentStage = application.current_stage;
  while (currentStage !== "offer") {
    const stage = stages.find((item) => item.stage_type === currentStage);
    expect(stage).toBeTruthy();
    const advanced = await apiPost<{ current_stage: string }>(
      request,
      `/api/v1/recruitment/applications/${application.id}/advance`,
      headers,
      {
        stage_id: stage!.id,
        result: "pass",
      },
      200,
    );
    currentStage = advanced.current_stage;
  }

  return application.id;
}

async function createOfferFlow(
  request: APIRequestContext,
  headers: Record<string, string>,
  data: {
    suffix: string;
    primaryDepartment: Department;
    secondaryDepartment: Department;
    primaryPosition: Position;
    secondaryPosition: Position;
    accepted: boolean;
    officialSalary: number;
  },
): Promise<OfferFlowSeed> {
  const jrId = await createApprovedJr(request, headers, {
    positionId: data.primaryPosition.id,
    departmentId: data.primaryDepartment.id,
  });
  const candidate = await createCandidate(request, headers, data.suffix);
  const applicationId = await applyAndAdvanceToOffer(request, headers, {
    candidateId: candidate.id,
    jrId,
  });

  const offer = await apiPost<{ id: number }>(
    request,
    `/api/v1/recruitment/applications/${applicationId}/offers`,
    headers,
    {
      job_position_id: data.primaryPosition.id,
      department_id: data.primaryDepartment.id,
      proposed_start_date: "2026-08-01",
      probation_salary: 10000000,
      official_salary: data.officialSalary,
      probation_days: 30,
      expires_at: "2026-07-15",
    },
  );

  if (data.accepted) {
    await apiPost(request, `/api/v1/recruitment/offers/${offer.id}/send`, headers, {}, 200);
    await apiPost(request, `/api/v1/recruitment/offers/${offer.id}/accept`, headers, {}, 200);
  }

  return {
    applicationId,
    offerId: offer.id,
    primaryDepartment: data.primaryDepartment,
    secondaryDepartment: data.secondaryDepartment,
    primaryPosition: data.primaryPosition,
    secondaryPosition: data.secondaryPosition,
  };
}

async function openSelectOptions(page: Page, label: string) {
  const field = page.locator(".rc-field").filter({ has: page.getByText(label, { exact: false }) }).first();
  await field.locator(".p-select").click();
  const overlay = page.locator(".p-select-overlay:visible").last();
  const options = overlay.locator('[role="option"]');
  await expect(options.first()).toBeVisible();
  const texts = (await options.allTextContents()).map((item) => item.trim()).filter(Boolean);
  return { field, overlay, options, texts };
}

async function selectOptionByText(page: Page, label: string, optionText: string) {
  const { overlay } = await openSelectOptions(page, label);
  await overlay.getByRole("option", { name: optionText, exact: true }).click();
}

test.describe("Recruitment department-scoped position selects", () => {
  test("edit offer dialog and hiring decision dialog reload positions when department changes", async ({ page, request }) => {
    const headers = await authHeaders(request);
    const suffix = String(Date.now()).slice(-8);
    const jobTitleId = await getAnyJobTitleId(request, headers);

    const primaryDepartment = await createDepartment(
      request,
      headers,
      `OFD${suffix}`,
      `Phòng Offer ${suffix}`,
    );
    const secondaryDepartment = await createDepartment(
      request,
      headers,
      `OFS${suffix}`,
      `Phòng Offer 2 ${suffix}`,
    );

    const primaryPosition = await createPosition(request, headers, {
      code: `POSA${suffix}`,
      name: `Vị trí Offer A ${suffix}`,
      department_id: primaryDepartment.id,
      job_title_id: jobTitleId,
    });
    const secondaryPosition = await createPosition(request, headers, {
      code: `POSB${suffix}`,
      name: `Vị trí Offer B ${suffix}`,
      department_id: secondaryDepartment.id,
      job_title_id: jobTitleId,
    });

    const draftFlow = await createOfferFlow(request, headers, {
      suffix: `${suffix}A`,
      primaryDepartment,
      secondaryDepartment,
      primaryPosition,
      secondaryPosition,
      accepted: false,
      officialSalary: 11111111,
    });

    const acceptedFlow = await createOfferFlow(request, headers, {
      suffix: `${suffix}B`,
      primaryDepartment,
      secondaryDepartment,
      primaryPosition,
      secondaryPosition,
      accepted: true,
      officialSalary: 22222222,
    });

    await login(page, `/recruitment/applications/${draftFlow.applicationId}`);
    await page.getByRole("tab", { name: "Offer & Tuyển dụng" }).click();
    await page.getByRole("row").filter({ hasText: "11.111.111 ₫" }).getByRole("button").nth(1).click();

    const offerDialog = page.getByRole("dialog", { name: "Chỉnh sửa Offer" });
    await expect(offerDialog).toBeVisible();

    const offerDepartments = await openSelectOptions(page, "Phòng ban");
    expect(offerDepartments.texts).toContain(primaryDepartment.name);
    expect(offerDepartments.texts).toContain(secondaryDepartment.name);
    await page.keyboard.press("Escape");

    await selectOptionByText(page, "Phòng ban", secondaryDepartment.name);
    await page.waitForTimeout(600);

    const offerPositions = await openSelectOptions(page, "Vị trí tuyển dụng");
    expect(offerPositions.texts).toContain(secondaryPosition.name);
    expect(offerPositions.texts).not.toContain(primaryPosition.name);
    await page.keyboard.press("Escape");
    await offerDialog.getByRole("button", { name: "Hủy" }).click();

    await page.goto(`/recruitment/applications/${acceptedFlow.applicationId}`);
    await page.getByRole("tab", { name: "Offer & Tuyển dụng" }).click();
    await page.getByRole("row").filter({ hasText: "22.222.222 ₫" }).getByRole("button", { name: "Quyết định" }).click();

    const decisionDialog = page.getByRole("dialog", { name: "Quyết định tuyển dụng" });
    await expect(decisionDialog).toBeVisible();

    const decisionDepartments = await openSelectOptions(page, "Phòng ban");
    expect(decisionDepartments.texts).toContain(primaryDepartment.name);
    expect(decisionDepartments.texts).toContain(secondaryDepartment.name);
    await page.keyboard.press("Escape");

    await selectOptionByText(page, "Phòng ban", secondaryDepartment.name);
    await page.waitForTimeout(600);

    const decisionPositions = await openSelectOptions(page, "Vị trí");
    expect(decisionPositions.texts).toContain(secondaryPosition.name);
    expect(decisionPositions.texts).not.toContain(primaryPosition.name);
    await page.keyboard.press("Escape");
  });
});
