import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

type DepartmentNode = {
  id: number;
  code: string;
  name: string;
};

type EmployeeNode = {
  id: number;
  full_name: string;
};

type ContractCategoryNode = {
  id: number;
};

type RoleNode = {
  id: number;
  code: string;
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

async function createDepartment(
  request: APIRequestContext,
  token: string,
  payload: { code: string; name: string; dept_type: string; parent_id?: number },
): Promise<DepartmentNode> {
  const response = await request.post("/api/v1/departments", {
    headers: { Authorization: `Bearer ${token}` },
    data: payload,
  });
  expect(response.ok()).toBeTruthy();
  return await response.json() as DepartmentNode;
}

async function createEmployee(
  request: APIRequestContext,
  token: string,
  payload: {
    suffix: string;
    fullName: string;
    departmentId: number;
    personalEmail: string;
  },
): Promise<EmployeeNode> {
  const response = await request.post("/api/v1/employees", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      employee_code_sequence_id: 1,
      full_name: payload.fullName,
      last_name: payload.fullName.split(" ")[0],
      first_name: payload.fullName.split(" ").slice(-1)[0],
      date_of_birth: "1990-01-01",
      gender: "male",
      nationality_id: 1,
      id_number: `E2ECON${payload.suffix}`,
      id_issued_on: "2020-01-01",
      id_issued_by: "CA Test",
      status: "official",
      start_date: "2026-01-01",
      personal_email: payload.personalEmail,
      initial_department_id: payload.departmentId,
      initial_job_effective_from: "2026-01-01",
    },
  });
  expect(response.ok()).toBeTruthy();
  return await response.json() as EmployeeNode;
}

async function getFirstContractCategory(
  request: APIRequestContext,
  token: string,
): Promise<ContractCategoryNode> {
  const response = await request.get("/api/v1/lookups/contract-categories?limit=1", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json() as ContractCategoryNode[];
  expect(payload.length).toBeGreaterThan(0);
  return payload[0];
}

async function createContract(
  request: APIRequestContext,
  token: string,
  payload: {
    employeeId: number;
    contractCategoryId: number;
    contractNumber: string;
    effectiveTo: string;
  },
) {
  const response = await request.post(`/api/v1/employees/${payload.employeeId}/contracts`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      contract_category_id: payload.contractCategoryId,
      contract_number: payload.contractNumber,
      signed_date: "2026-01-01",
      effective_from: "2026-01-01",
      effective_to: payload.effectiveTo,
      insurance_salary_mode: "fixed_manual",
      insurance_salary_fixed_amount: "5000000",
    },
  });
  expect(response.ok()).toBeTruthy();
  return await response.json();
}

async function createScopedHrOfficer(
  request: APIRequestContext,
  adminToken: string,
  payload: {
    email: string;
    fullName: string;
    password: string;
    departmentIds: number[];
  },
): Promise<void> {
  const userResponse = await request.post("/api/v1/users", {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: {
      email: payload.email,
      full_name: payload.fullName,
      password: payload.password,
    },
  });
  expect(userResponse.ok()).toBeTruthy();
  const user = await userResponse.json() as { id: number };

  const rolesResponse = await request.get("/api/v1/roles", {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  expect(rolesResponse.ok()).toBeTruthy();
  const roles = await rolesResponse.json() as RoleNode[];
  const hrOfficerRole = roles.find((role) => role.code === "hr_officer");
  expect(hrOfficerRole).toBeTruthy();

  const assignResponse = await request.post(`/api/v1/users/${user.id}/roles`, {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: {
      role_id: hrOfficerRole!.id,
      scope_type: "department",
      department_ids: payload.departmentIds,
    },
  });
  expect(assignResponse.ok()).toBeTruthy();
}

test("scoped hr officer only sees contracts within assigned department tree on UI", async ({ page, request }) => {
  const adminToken = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const suffix = `${Date.now()}`;
  const shortSuffix = suffix.slice(-8);
  const scopedUserEmail = `e2e.contract.scope.${suffix}@example.com`;
  const scopedUserPassword = "ContractScope@1234";

  const rootDepartment = await createDepartment(request, adminToken, {
    code: `E2ECR${suffix.slice(-6)}`,
    name: `E2E Contract Root ${suffix}`,
    dept_type: "PHONG",
  });
  const childDepartment = await createDepartment(request, adminToken, {
    code: `E2ECC${suffix.slice(-6)}`,
    name: `E2E Contract Child ${suffix}`,
    dept_type: "BO_PHAN",
    parent_id: rootDepartment.id,
  });
  const outsideDepartment = await createDepartment(request, adminToken, {
    code: `E2ECO${suffix.slice(-6)}`,
    name: `E2E Contract Outside ${suffix}`,
    dept_type: "PHONG",
  });

  const visibleEmployee = await createEmployee(request, adminToken, {
    suffix: `${shortSuffix}01`,
    fullName: `E2E Visible Contract ${suffix}`,
    departmentId: childDepartment.id,
    personalEmail: `e2e.visible.${suffix}@example.com`,
  });
  const hiddenEmployee = await createEmployee(request, adminToken, {
    suffix: `${shortSuffix}02`,
    fullName: `E2E Hidden Contract ${suffix}`,
    departmentId: outsideDepartment.id,
    personalEmail: `e2e.hidden.${suffix}@example.com`,
  });

  const contractCategory = await getFirstContractCategory(request, adminToken);
  const visibleContractNumber = `E2E-CON-VISIBLE-${suffix}`;
  const hiddenContractNumber = `E2E-CON-HIDDEN-${suffix}`;

  await createContract(request, adminToken, {
    employeeId: visibleEmployee.id,
    contractCategoryId: contractCategory.id,
    contractNumber: visibleContractNumber,
    effectiveTo: "2026-07-15",
  });
  await createContract(request, adminToken, {
    employeeId: hiddenEmployee.id,
    contractCategoryId: contractCategory.id,
    contractNumber: hiddenContractNumber,
    effectiveTo: "2026-07-20",
  });

  await createScopedHrOfficer(request, adminToken, {
    email: scopedUserEmail,
    fullName: `E2E Scoped HR Officer ${suffix}`,
    password: scopedUserPassword,
    departmentIds: [rootDepartment.id],
  });

  const scopedToken = await loginViaApi(request, scopedUserEmail, scopedUserPassword);
  const meResponse = await request.get("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${scopedToken}` },
  });
  expect(meResponse.ok()).toBeTruthy();
  const mePayload = await meResponse.json() as {
    department_scopes?: Record<string, number[]>;
  };
  expect(mePayload.department_scopes?.contracts).toEqual([rootDepartment.id, childDepartment.id]);

  await loginViaUi(page, scopedUserEmail, scopedUserPassword);

  const nav = page.locator("nav");
  await expect(nav.locator('a[href="/contracts"]')).toBeVisible();

  const contractsResponsePromise = page.waitForResponse((response) => {
    return response.url().includes("/api/v1/contracts") && response.status() === 200;
  });
  await page.goto("/contracts");
  await page.waitForLoadState("networkidle");

  const contractsResponse = await contractsResponsePromise;
  const contractsPayload = await contractsResponse.json() as {
    items: Array<{ contract_number: string; employee_name?: string | null }>;
  };
  const contractNumbers = contractsPayload.items.map((item) => item.contract_number);
  expect(contractNumbers).toContain(visibleContractNumber);
  expect(contractNumbers).not.toContain(hiddenContractNumber);

  await expect(page.getByRole("heading", { name: "Hợp đồng lao động" })).toBeVisible();
  await expect(page.getByText(visibleContractNumber, { exact: true })).toBeVisible();
  await expect(page.getByText(`E2E Visible Contract ${suffix}`, { exact: true })).toBeVisible();
  await expect(page.getByText(hiddenContractNumber, { exact: true })).toHaveCount(0);
  await expect(page.getByText(`E2E Hidden Contract ${suffix}`, { exact: true })).toHaveCount(0);
});
