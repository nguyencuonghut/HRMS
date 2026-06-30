import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || "Hrms@2026";
const LINE_MANAGER_EMAIL = process.env.E2E_LINE_MANAGER_EMAIL || "linemanager@hrms.local";
const LINE_MANAGER_PASSWORD = process.env.E2E_LINE_MANAGER_PASSWORD || "Hrms@2026";

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

function collectDepartmentIds(nodes: Array<{ id: number; children?: unknown[] }>): number[] {
  const result: number[] = [];
  for (const node of nodes) {
    result.push(node.id);
    const children = Array.isArray(node.children) ? node.children : [];
    result.push(...collectDepartmentIds(children as Array<{ id: number; children?: unknown[] }>));
  }
  return result;
}

test("line manager only sees org UI within assigned department scope", async ({ page, request }) => {
  const adminToken = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const lineManagerToken = await loginViaApi(request, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

  const meResponse = await request.get("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${lineManagerToken}` },
  });
  expect(meResponse.ok()).toBeTruthy();
  const mePayload = await meResponse.json();
  const orgScope = Array.isArray(mePayload.department_scopes?.org) ? mePayload.department_scopes.org as number[] : [];
  expect(orgScope.length).toBeGreaterThan(0);

  const departmentListResponse = await request.get("/api/v1/departments", {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  expect(departmentListResponse.ok()).toBeTruthy();
  const allDepartments = await departmentListResponse.json() as Array<{ id: number }>;
  const outsideDepartment = allDepartments.find((item) => !orgScope.includes(item.id));
  expect(outsideDepartment).toBeTruthy();

  await loginViaUi(page, LINE_MANAGER_EMAIL, LINE_MANAGER_PASSWORD);

  const nav = page.locator("nav");
  await expect(nav.locator('a[href="/org/departments"]')).toBeVisible();
  await expect(nav.locator('a[href="/org/positions"]')).toBeVisible();
  await expect(nav.locator('a[href="/org/job-titles"]')).toHaveCount(0);
  await expect(nav.locator('a[href="/org/history"]')).toHaveCount(0);

  const treeResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/departments/tree") && response.status() === 200;
  });
  await page.goto("/org/departments");
  const treeResponse = await treeResponsePromise;
  const treePayload = await treeResponse.json() as Array<{ id: number; children?: unknown[] }>;
  const visibleDepartmentIds = collectDepartmentIds(treePayload);
  expect(visibleDepartmentIds.length).toBeGreaterThan(0);
  expect(visibleDepartmentIds.every((departmentId) => orgScope.includes(departmentId))).toBeTruthy();

  await page.goto(`/org/departments/${outsideDepartment!.id}`);
  await page.waitForURL("**/forbidden");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();

  await page.goto("/org/job-titles");
  await page.waitForURL("**/forbidden");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();

  await page.goto("/org/history");
  await page.waitForURL("**/forbidden");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
});
