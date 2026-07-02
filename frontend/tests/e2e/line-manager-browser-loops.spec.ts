import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || "Hrms@2026";
const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";

type EmployeeLookupItem = {
  id: number;
  display_code: string;
  full_name: string;
};

type RewardTypeRead = {
  id: number;
  name: string;
  is_monetary: boolean;
};

async function loginViaUi(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByPlaceholder("Nhập mật khẩu").fill(password);

  const meResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/auth/me") && response.status() === 200;
  });

  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await meResponse;
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

async function fetchEmployeeLookup(
  request: APIRequestContext,
  token: string,
  limit = 500,
): Promise<EmployeeLookupItem[]> {
  const response = await request.get(`/api/v1/employees/lookup?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as EmployeeLookupItem[];
}

test("line manager employee browser loop only exposes employees in assigned subtree", async ({ page, request }) => {
  const adminToken = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const managerToken = await loginViaApi(request, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

  const scopedEmployees = await fetchEmployeeLookup(request, managerToken);
  const allEmployees = await fetchEmployeeLookup(request, adminToken);

  expect(scopedEmployees.length).toBeGreaterThan(0);
  const inScopeEmployee = scopedEmployees[0];
  const scopedIds = new Set(scopedEmployees.map((item) => item.id));
  const outsideEmployee = allEmployees.find((item) => !scopedIds.has(item.id));
  expect(outsideEmployee).toBeTruthy();

  await loginViaUi(page, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

  await page.goto("/employees");
  await page.waitForLoadState("networkidle");

  const searchInput = page.getByPlaceholder("Tìm tên, CCCD, SĐT...");

  const inScopeSearchResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/employees") && response.status() === 200;
  });
  await searchInput.fill(inScopeEmployee.full_name);
  await searchInput.press("Enter");
  await inScopeSearchResponse;
  await page.waitForLoadState("networkidle");

  const table = page.locator(".p-datatable");
  await expect(table).toContainText(inScopeEmployee.full_name);
  await expect(table).toContainText(inScopeEmployee.display_code);

  const outOfScopeSearchResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/employees") && response.status() === 200;
  });
  await searchInput.fill(outsideEmployee!.full_name);
  await searchInput.press("Enter");
  await outOfScopeSearchResponse;
  await page.waitForLoadState("networkidle");

  await expect(table).not.toContainText(outsideEmployee!.full_name);
  await expect(page.getByText("Không có nhân viên nào")).toBeVisible();

  const reopenInScopeResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/employees") && response.status() === 200;
  });
  await searchInput.fill(inScopeEmployee.full_name);
  await searchInput.press("Enter");
  await reopenInScopeResponse;
  await page.waitForLoadState("networkidle");

  const employeeRow = table.locator("tbody tr").filter({ hasText: inScopeEmployee.full_name }).first();
  const employeeLink = employeeRow.locator("a.name-cell-button").first();
  await expect(employeeLink).toHaveAttribute("href", `/employees/${inScopeEmployee.id}`);
  await employeeLink.click();
  await page.waitForURL(new RegExp(`.*/employees/${inScopeEmployee.id}$`));
  await expect(page.getByRole("heading", { name: inScopeEmployee.full_name })).toBeVisible();

  await page.goto(`/employees/${outsideEmployee!.id}`);
  await page.waitForURL("**/forbidden");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
});

test("line manager rewards browser loop scopes create dialog and can create in-scope reward plus export report", async ({ page, request }) => {
  const adminToken = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const managerToken = await loginViaApi(request, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

  const scopedEmployees = await fetchEmployeeLookup(request, managerToken);
  const allEmployees = await fetchEmployeeLookup(request, adminToken);
  const rewardTypesResponse = await request.get("/api/v1/rewards/types", {
    headers: { Authorization: `Bearer ${managerToken}` },
  });
  expect(rewardTypesResponse.ok()).toBeTruthy();
  const rewardTypes = (await rewardTypesResponse.json()) as RewardTypeRead[];

  expect(scopedEmployees.length).toBeGreaterThan(0);
  expect(rewardTypes.length).toBeGreaterThan(0);

  const inScopeEmployee = scopedEmployees[0];
  const scopedIds = new Set(scopedEmployees.map((item) => item.id));
  const outsideEmployee = allEmployees.find((item) => !scopedIds.has(item.id));
  expect(outsideEmployee).toBeTruthy();

  const selectedRewardType = rewardTypes.find((item) => !item.is_monetary) ?? rewardTypes[0];
  const uniqueStamp = Date.now();
  const decisionNumber = `LM-E2E-${uniqueStamp}`;
  const rewardTitle = `Khen thưởng scope ${uniqueStamp}`;
  let createdRewardId: number | null = null;

  try {
    await loginViaUi(page, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

    const lookupResponsePromise = page.waitForResponse((response) => {
      return response.url().includes("/api/v1/employees/lookup") && response.status() === 200;
    });
    await page.goto("/rewards");
    const lookupResponse = await lookupResponsePromise;
    const rewardLookupEmployees = (await lookupResponse.json()) as EmployeeLookupItem[];
    await page.waitForLoadState("networkidle");

    expect(rewardLookupEmployees.some((item) => item.id === inScopeEmployee.id)).toBeTruthy();
    expect(rewardLookupEmployees.some((item) => item.id === outsideEmployee!.id)).toBeFalsy();

    await expect(page.locator(".p-datatable")).not.toContainText(outsideEmployee!.full_name);

    await page.getByRole("button", { name: "Thêm quyết định" }).click();
    const rewardDialog = page.locator(".p-dialog").filter({ hasText: "Thêm quyết định khen thưởng" }).first();
    await expect(rewardDialog).toBeVisible();

    const employeeSelect = page.getByPlaceholder("Chọn nhân viên...");
    await employeeSelect.click();
    const visibleOptions = page.locator(".p-select-overlay:visible [role='option']");
    await expect(visibleOptions.filter({ hasText: inScopeEmployee.full_name }).first()).toBeVisible();
    await expect(visibleOptions.filter({ hasText: outsideEmployee!.full_name })).toHaveCount(0);
    await visibleOptions.filter({ hasText: inScopeEmployee.full_name }).first().click();

    await page.getByPlaceholder("Chọn loại...").click();
    await page.locator(".p-select-overlay:visible [role='option']").filter({ hasText: selectedRewardType.name }).first().click();

    await page.getByPlaceholder("VD: Khen thưởng tháng 05/2026").fill(rewardTitle);
    await page.getByPlaceholder("VD: 01/QĐ-2026").fill(decisionNumber);
    if (selectedRewardType.is_monetary) {
      await page.getByPlaceholder("500.000").fill("100000");
    }

    const createResponsePromise = page.waitForResponse((response) => {
      return response.url().endsWith("/api/v1/rewards") && response.request().method() === "POST" && response.status() === 201;
    });
    await rewardDialog.getByRole("button", { name: "Thêm", exact: true }).click();
    const createResponse = await createResponsePromise;
    const createdReward = await createResponse.json();
    createdRewardId = createdReward.id as number;
    expect(createdReward.employee_id).toBe(inScopeEmployee.id);

    await expect(page.getByText("Quyết định khen thưởng đã được tạo")).toBeVisible();

    const rewardSearch = page.getByPlaceholder("Tìm mã NV, tên, số QĐ...").first();
    const rewardsReloadResponse = page.waitForResponse((response) => {
      return response.url().includes("/api/v1/rewards?") && response.status() === 200;
    });
    await rewardSearch.fill(decisionNumber);
    await rewardSearch.press("Enter");
    await rewardsReloadResponse;
    await page.waitForLoadState("networkidle");

    const rewardTable = page.locator(".p-datatable").first();
    await expect(rewardTable).toContainText(decisionNumber);
    await expect(rewardTable).toContainText(inScopeEmployee.full_name);

    await page.getByRole("button", { name: "Xem báo cáo khen thưởng & kỷ luật" }).click();
    await page.waitForURL("**/reports/rewards");

    const reportResponsePromise = page.waitForResponse((response) => {
      return response.url().includes("/api/v1/rewards/report/summary") && response.status() === 200;
    });
    await page.getByRole("button", { name: "Xem báo cáo" }).click();
    await reportResponsePromise;
    await page.waitForLoadState("networkidle");

    const reportPage = page.locator(".report-canonical-page");
    await expect(reportPage).toContainText(decisionNumber);
    await expect(reportPage).toContainText(inScopeEmployee.full_name);
    await expect(reportPage).not.toContainText(outsideEmployee!.full_name);

    const exportResponsePromise = page.waitForResponse((response) => {
      return response.url().includes("/api/v1/rewards/report/export") && response.status() === 200;
    });
    await page.getByRole("button", { name: "Xuất Excel" }).click();
    const exportResponse = await exportResponsePromise;
    expect(exportResponse.headers()["content-type"] || "").toContain("spreadsheetml");
  } finally {
    if (createdRewardId) {
      await request.delete(`/api/v1/rewards/${createdRewardId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
    }
  }
});
