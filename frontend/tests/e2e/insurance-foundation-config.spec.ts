import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

async function login(page: Page, redirect = "/reports/dashboard") {
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

async function fillDateField(page: Page, scope: Locator, fieldLabel: RegExp, value: string) {
  const field = scope.locator(".field").filter({ hasText: fieldLabel });
  const input = field.locator("input");
  await input.click();
  await input.fill(value);
  await input.press("Tab");
  const overlay = page.locator(".p-datepicker-panel[aria-label='Choose Date']");
  if (await overlay.count()) {
    const visible = await overlay.first().isVisible().catch(() => false);
    if (visible) {
      await page.keyboard.press("Escape");
      await expect(overlay.first()).toBeHidden();
    }
  }
}

test("insurance foundation view manages minimum wages and seniority settings", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1200 });
  await login(page, "/catalog/insurance");
  await page.waitForLoadState("networkidle");

  await expect(page.getByRole("heading", { name: "Lương tối thiểu vùng" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rule thâm niên BHXH" })).toBeVisible();

  const wageEffectiveFrom = "2032-01-01";
  await page.getByRole("button", { name: "Thêm cấu hình LTTV" }).click();
  const wageDialog = page.getByRole("dialog", { name: "Thêm cấu hình lương tối thiểu vùng" });
  await wageDialog.locator(".field").filter({ hasText: /^Vùng/ }).locator(".p-select").click();
  await page.getByRole("option", { name: "Vùng III" }).click();
  await wageDialog.locator(".field").filter({ hasText: /^Ngày hiệu lực/ }).locator("input").fill(wageEffectiveFrom);
  await wageDialog.locator(".field").filter({ hasText: /^Mức lương tối thiểu/ }).locator("input").fill("4300000");
  await wageDialog.locator(".field").filter({ hasText: /^Nghị định/ }).locator("input").fill("E2E/2032/ND-CP");
  await wageDialog.locator(".field").filter({ hasText: /^Ghi chú/ }).locator("textarea").fill("E2E_MIN_WAGE");
  const createWage = page.waitForResponse((response) =>
    response.url().includes("/api/v1/insurance/minimum-wages") &&
    response.request().method() === "POST",
  );
  await wageDialog.getByRole("button", { name: "Thêm cấu hình" }).click();
  expect((await createWage).status()).toBe(201);
  await expect(page.getByText("Đã thêm cấu hình lương tối thiểu vùng")).toBeVisible();

  const wageRow = page.locator("tr").filter({ hasText: "E2E/2032/ND-CP" }).first();
  await expect(wageRow).toBeVisible();
  await expect(wageRow.getByText("4.300.000")).toBeVisible();

  const deleteWage = page.waitForResponse((response) =>
    response.url().match(/\/api\/v1\/insurance\/minimum-wages\/\d+$/) !== null &&
    response.request().method() === "DELETE",
  );
  await wageRow.getByRole("button").nth(1).click();
  const wageConfirm = page.locator(".p-confirmdialog:visible");
  await wageConfirm.getByRole("button", { name: "Xóa" }).click();
  expect((await deleteWage).status()).toBe(204);
  await expect(page.getByText("Đã xóa cấu hình lương tối thiểu vùng")).toBeVisible();
  await expect(wageRow).toHaveCount(0);

  const seniorityEffectiveFrom = "2033-01-01";
  await page.getByRole("button", { name: "Thêm rule thâm niên" }).click();
  const seniorityDialog = page.getByRole("dialog", { name: "Thêm rule thâm niên BHXH" });
  await seniorityDialog.locator(".field").filter({ hasText: /^Tháng nâng bậc/ }).locator("input").fill("2");
  await seniorityDialog.locator(".field").filter({ hasText: /^Ngày nâng bậc/ }).locator("input").fill("1");
  await seniorityDialog.locator(".field").filter({ hasText: /^Số năm \/ bậc/ }).locator("input").fill("4");
  await seniorityDialog.locator(".field").filter({ hasText: /^Tháng cutoff năm đầu/ }).locator("input").fill("5");
  await seniorityDialog.locator(".field").filter({ hasText: /^Ngày cutoff năm đầu/ }).locator("input").fill("15");
  await seniorityDialog.locator(".field").filter({ hasText: /^Ngày hiệu lực/ }).locator("input").fill(seniorityEffectiveFrom);
  await seniorityDialog.locator(".field").filter({ hasText: /^Ghi chú/ }).locator("textarea").fill("E2E_SENIORITY");
  const createSeniority = page.waitForResponse((response) =>
    response.url().includes("/api/v1/insurance/seniority-settings") &&
    response.request().method() === "POST",
  );
  await seniorityDialog.getByRole("button", { name: "Thêm rule" }).click();
  expect((await createSeniority).status()).toBe(201);
  await expect(page.getByText("Đã thêm rule thâm niên BHXH")).toBeVisible();

  const seniorityRow = page.locator("tr").filter({ hasText: "15/05" }).filter({ hasText: "4 năm / 1 bậc" }).first();
  await expect(seniorityRow).toBeVisible();

  const deleteSeniority = page.waitForResponse((response) =>
    response.url().match(/\/api\/v1\/insurance\/seniority-settings\/\d+$/) !== null &&
    response.request().method() === "DELETE",
  );
  await seniorityRow.getByRole("button").nth(1).click();
  const seniorityConfirm = page.locator(".p-confirmdialog:visible");
  await seniorityConfirm.getByRole("button", { name: "Xóa" }).click();
  expect((await deleteSeniority).status()).toBe(200);
  await expect(page.getByText("Đã xóa rule thâm niên BHXH")).toBeVisible();
  await expect(seniorityRow).toHaveCount(0);
});

test("insurance foundation view manages bhxh position groups with 7 grades", async ({ page, request }) => {
  const token = await adminToken(request);
  const stamp = String(Date.now()).slice(-6);
  const deptCode = `EDB${stamp}`;
  const posCode = `EPB${stamp}`;
  const groupCode = `EBG${stamp}`;
  const positionName = `E2E Position BHXH ${stamp}`;
  let deptId: number | null = null;
  let positionId: number | null = null;
  let groupId: number | null = null;

  try {
    const deptResp = await request.post("/api/v1/departments", {
      data: { code: deptCode, name: `E2E Dept BHXH ${stamp}`, dept_type: "PHONG" },
    });
    expect(deptResp.status()).toBe(201);
    const dept = await deptResp.json();
    deptId = dept.id;

    const posResp = await request.post("/api/v1/job-positions", {
      data: { code: posCode, name: positionName, department_id: dept.id },
    });
    expect(posResp.status()).toBe(201);
    const position = await posResp.json();
    positionId = position.id;

    await page.setViewportSize({ width: 1600, height: 1200 });
    await login(page, "/catalog/insurance");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Nhóm vị trí BHXH + hệ số 7 bậc" })).toBeVisible();
    await page.getByRole("button", { name: "Thêm nhóm vị trí BHXH" }).click();
    const dialog = page.getByRole("dialog", { name: "Thêm nhóm vị trí BHXH" });
    await dialog.locator(".field").filter({ hasText: /^Mã nhóm/ }).locator("input").fill(groupCode);
    await dialog.locator(".field").filter({ hasText: /^Tên nhóm/ }).locator("input").fill(`Nhóm BHXH ${stamp}`);
    await dialog.locator(".field").filter({ hasText: /^Mô tả/ }).locator("textarea").fill("E2E position group");
    await dialog.locator(".field").filter({ hasText: /^Vị trí công việc thuộc nhóm/ }).locator(".p-multiselect").click();
    await page.getByRole("option", { name: new RegExp(posCode) }).click();
    await page.keyboard.press("Escape");

    for (let idx = 0; idx < 7; idx += 1) {
      const row = dialog.locator("tbody tr").nth(idx);
      await row.locator("input").nth(0).fill((1.1 + idx * 0.1).toFixed(2));
      await row.locator("input").nth(1).fill("12");
      await row.locator("input").nth(2).fill(`E2E grade ${idx + 1}`);
    }

    const createGroup = page.waitForResponse((response) =>
      response.url().includes("/api/v1/insurance/position-groups") &&
      response.request().method() === "POST",
    );
    await dialog.getByRole("button", { name: "Thêm nhóm" }).click();
    expect((await createGroup).status()).toBe(201);
    await expect(page.getByText("Đã thêm nhóm vị trí BHXH")).toBeVisible();

    const catalogResp = await request.get("/api/v1/insurance/position-groups", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(catalogResp.status()).toBe(200);
    const catalog = await catalogResp.json();
    groupId = catalog.groups.find((group: { code: string; id: number }) => group.code === groupCode)?.id ?? null;

    const groupRow = page.locator("tr").filter({ hasText: groupCode }).first();
    await expect(groupRow).toBeVisible();
    await expect(groupRow.getByText(positionName)).toBeVisible();
    await expect(groupRow.getByText("B1: 1.10")).toBeVisible();
    await expect(groupRow.getByText("B7: 1.70")).toBeVisible();

    const deleteGroup = page.waitForResponse((response) =>
      response.url().match(/\/api\/v1\/insurance\/position-groups\/\d+$/) !== null &&
      response.request().method() === "DELETE",
    );
    await groupRow.getByRole("button").nth(1).click();
    const confirm = page.locator(".p-confirmdialog:visible");
    await confirm.getByRole("button", { name: "Xóa" }).click();
    expect((await deleteGroup).status()).toBe(200);
    groupId = null;
    await expect(page.getByText("Đã xóa nhóm vị trí BHXH")).toBeVisible();
    await expect(groupRow).toHaveCount(0);
  } finally {
    if (groupId) {
      await request.delete(`/api/v1/insurance/position-groups/${groupId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    }
    if (positionId) {
      await request.delete(`/api/v1/job-positions/${positionId}`);
    }
    if (deptId) {
      await request.delete(`/api/v1/departments/${deptId}`);
    }
  }
});

test("employee contract form supports computed and fixed insurance salary modes", async ({ page, request }) => {
  const token = await adminToken(request);
  const stamp = String(Date.now()).slice(-6);
  const computedNumber = `E2E-BHXH-C-${stamp}`;
  const fixedNumber = `E2E-BHXH-F-${stamp}`;

  try {
    await page.setViewportSize({ width: 1600, height: 1200 });
    await login(page, "/employees/1");
    await page.waitForLoadState("networkidle");

    await page.getByRole("tab", { name: "Hợp đồng" }).click();
    await expect(page.getByRole("button", { name: "Thêm hợp đồng" })).toBeVisible();

    await page.getByRole("button", { name: "Thêm hợp đồng" }).click();
    const computedDialog = page.getByRole("dialog", { name: "Thêm hợp đồng" });
    await computedDialog.locator(".field").filter({ hasText: /^Loại hợp đồng/ }).locator(".p-select").click();
    await page.getByRole("option", { name: "HĐLĐ xác định thời hạn (HĐ)" }).click();
    await computedDialog.locator(".field").filter({ hasText: /^Số hợp đồng/ }).locator("input").fill(computedNumber);
    await fillDateField(page, computedDialog, /^Ngày ký/, "01/01/2026");
    await fillDateField(page, computedDialog, /^Hiệu lực từ/, "01/01/2026");
    await computedDialog.locator(".field").filter({ hasText: /^Mode lương đóng BH/ }).locator(".p-select").click();
    await page.getByRole("option", { name: "Theo nhóm vị trí + bậc" }).click();
    await computedDialog.locator(".field").filter({ hasText: /^Nhóm vị trí BHXH/ }).locator(".p-select").click();
    await page.getByRole("option", { name: /OFFICE_STAFF/ }).click();
    await computedDialog.locator(".field").filter({ hasText: /^Bậc hệ số/ }).locator(".p-select").click();
    const previewResp = page.waitForResponse((response) =>
      response.url().includes("/preview-insurance-salary") &&
      response.request().method() === "POST",
    );
    await page.getByRole("option", { name: "Bậc 3" }).click();
    expect((await previewResp).status()).toBe(200);
    await expect(computedDialog.getByText(/5\.050\.800/)).toBeVisible();

    const createComputed = page.waitForResponse((response) =>
      response.url().match(/\/api\/v1\/employees\/1\/contracts$/) !== null &&
      response.request().method() === "POST",
    );
    await computedDialog.getByRole("button", { name: "Tạo hợp đồng" }).click();
    expect((await createComputed).status()).toBe(201);
    const computedCard = page.locator(".contract-card").filter({ hasText: computedNumber }).first();
    await expect(computedCard).toBeVisible();
    await expect(computedCard.getByText("Theo nhóm vị trí + bậc")).toBeVisible();
    await expect(computedCard.getByText(/5\.050\.800/)).toBeVisible();
    await expect(computedCard.getByText(/OFFICE_STAFF|Nhân viên Kế toán/)).toBeVisible();

    await page.getByRole("button", { name: "Thêm hợp đồng" }).click();
    const fixedDialog = page.getByRole("dialog", { name: "Thêm hợp đồng" });
    await fixedDialog.locator(".field").filter({ hasText: /^Loại hợp đồng/ }).locator(".p-select").click();
    await page.getByRole("option", { name: "HĐLĐ xác định thời hạn (HĐ)" }).click();
    await fixedDialog.locator(".field").filter({ hasText: /^Số hợp đồng/ }).locator("input").fill(fixedNumber);
    await fillDateField(page, fixedDialog, /^Ngày ký/, "01/01/2026");
    await fillDateField(page, fixedDialog, /^Hiệu lực từ/, "01/01/2026");
    await fixedDialog.locator(".field").filter({ hasText: /^Mode lương đóng BH/ }).locator(".p-select").click();
    await page.getByRole("option", { name: "Cố định theo thỏa thuận" }).click();
    const fixedAmountInput = fixedDialog
      .locator(".field")
      .filter({ hasText: /^Mức lương đóng BH cố định/ })
      .locator("input");
    await fixedAmountInput.fill("12345678");
    await fixedAmountInput.press("Tab");
    await expect(fixedDialog.getByText(/12\.345\.678/)).toBeVisible();

    const createFixed = page.waitForResponse((response) =>
      response.url().match(/\/api\/v1\/employees\/1\/contracts$/) !== null &&
      response.request().method() === "POST",
    );
    await fixedDialog.getByRole("button", { name: "Tạo hợp đồng" }).click();
    expect((await createFixed).status()).toBe(201);
    const fixedCard = page.locator(".contract-card").filter({ hasText: fixedNumber }).first();
    await expect(fixedCard).toBeVisible();
    await expect(fixedCard.getByText("Cố định theo thỏa thuận")).toBeVisible();
    await expect(fixedCard.getByText(/12\.345\.678/)).toBeVisible();
  } finally {
    const contractsResp = await request.get("/api/v1/employees/1/contracts", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (contractsResp.ok()) {
      const contracts = await contractsResp.json();
      for (const item of contracts.filter((row: { contract_number: string }) =>
        row.contract_number === computedNumber || row.contract_number === fixedNumber,
      )) {
        await request.delete(`/api/v1/employees/1/contracts/${item.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    }
  }
});
