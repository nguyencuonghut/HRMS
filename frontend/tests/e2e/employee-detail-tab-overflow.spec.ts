import { expect, test } from "@playwright/test";

test.describe("Employee detail tab overflow", () => {
  test.use({ viewport: { width: 1180, height: 900 } });

  test("keeps hidden tabs reachable through scroll navigators", async ({ page }) => {
    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      const { pathname } = url;
      const method = route.request().method();

      if (pathname.endsWith("/auth/refresh") && method === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ access_token: "mock-access-token", token_type: "bearer" }),
        });
        return;
      }

      if (pathname.endsWith("/auth/me") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: 1,
            email: "admin@hrms.local",
            full_name: "Admin HRMS",
            is_active: true,
            is_superuser: true,
            roles: ["admin"],
            permissions: ["*"],
          }),
        });
        return;
      }

      if (pathname.endsWith("/departments") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 1, code: "HCNS", name: "Phòng Hành chính nhân sự", is_active: true },
          ]),
        });
        return;
      }

      if (pathname.endsWith("/job-titles") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 1, code: "TP", name: "Trưởng phòng", level: 4, is_active: true },
          ]),
        });
        return;
      }

      if (pathname.endsWith("/job-positions") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 1, code: "CVHCNS", name: "Chuyên viên HCNS", department_id: 1, is_active: true },
          ]),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/employees/new");
    await page.waitForLoadState("networkidle");

    const nextButton = page.locator(".employee-detail-tabs .p-tablist-next-button");
    await expect(nextButton).toBeVisible();

    const targetTab = page.getByRole("tab", { name: "Checklist hồ sơ pháp lý" });

    for (let i = 0; i < 6; i += 1) {
      if (await targetTab.isVisible()) break;
      await nextButton.click();
    }

    await expect(targetTab).toBeVisible();
    await targetTab.click();

    const activePanel = page.getByRole("tabpanel", { name: "Checklist hồ sơ pháp lý" });
    await expect(activePanel).toBeVisible();
  });
});
