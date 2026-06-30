import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { isNetworkError } from "@/utils/network";
import { getDefaultAuthorizedRoute } from "@/router/defaultAuthorizedRoute";

// Khai báo kiểu cho route meta
declare module "vue-router" {
  interface RouteMeta {
    title?: string
    public?: boolean
    permission?: string   // permission code cần có — VD: 'users:view'
    anyPermissions?: string[]
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/auth/LoginView.vue"),
      meta: { public: true },
    },
    {
      path: "/forbidden",
      name: "forbidden",
      component: () => import("@/views/ForbiddenView.vue"),
      meta: { public: true },
    },
    {
      path: "/",
      component: () => import("@/components/layout/AppLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          redirect: "/reports/dashboard",
        },
        {
          path: "dashboard",
          redirect: "/reports/dashboard",
        },
        // Cơ cấu tổ chức
        {
          path: "org/job-titles",
          name: "org-job-titles",
          component: () => import("@/views/org/JobTitleListView.vue"),
          meta: { title: "Chức danh", permission: "org:view" },
        },
        {
          path: "org/departments",
          name: "org-departments",
          component: () => import("@/views/org/DepartmentListView.vue"),
          meta: { title: "Phòng / Ban", permission: "org:view" },
        },
        {
          path: "org/departments/:id",
          name: "org-department-detail",
          component: () => import("@/views/org/DepartmentDetailView.vue"),
          meta: { title: "Chi tiết phòng / Ban", permission: "org:view" },
        },
        {
          path: "org/positions",
          name: "org-positions",
          component: () => import("@/views/org/PositionListView.vue"),
          meta: { title: "Vị trí công việc", permission: "org:view" },
        },
        {
          path: "org/history",
          name: "org-history",
          component: () => import("@/views/org/OrgHistoryView.vue"),
          meta: { title: "Lịch sử thay đổi", permission: "org:view" },
        },
        // Nhân sự
        {
          path: "employees",
          name: "employees",
          component: () => import("@/views/employees/EmployeeListView.vue"),
          meta: { title: "Danh sách nhân viên", permission: "employees:view" },
        },
        {
          path: "employees/:id",
          name: "employee-detail",
          component: () => import("@/views/employees/EmployeeDetailView.vue"),
          meta: { title: "Hồ sơ nhân viên", permission: "employees:view" },
        },
        // Probation reports
        {
          path: "employees/probation-reports",
          name: "employees-probation-reports",
          redirect: { name: "probation-analytics" },
          meta: { title: "Báo cáo thử việc", permission: "employees:view" },
        },
        // Onboarding
        {
          path: "employees/onboarding/tasks",
          name: "onboarding-tasks",
          component: () =>
            import("@/views/employees/OnboardingTaskConfigView.vue"),
          meta: { title: "Cấu hình task onboarding", permission: "employees:edit" },
        },
        {
          path: "employees/onboarding/:employee_id",
          name: "onboarding-detail",
          component: () => import("@/views/employees/OnboardingDetailView.vue"),
          meta: { title: "Chi tiết onboarding", permission: "employees:view" },
        },
        {
          path: "employees/onboarding",
          name: "onboarding-list",
          component: () => import("@/views/employees/OnboardingListView.vue"),
          meta: { title: "Tiếp nhận nhân viên mới", permission: "employees:view" },
        },
        // Nhắc nhở sự kiện
        {
          path: "reminders",
          name: "reminders",
          component: () => import("@/views/RemindersView.vue"),
          meta: { title: "Nhắc nhở sự kiện", permission: "employees:view" },
        },
        // Hợp đồng
        {
          path: "contracts",
          name: "contracts",
          component: () => import("@/views/contracts/ContractListView.vue"),
          meta: { title: "Hợp đồng lao động", permission: "contracts:view" },
        },
        // Nghỉ phép
        {
          path: "leaves",
          name: "leaves",
          component: () => import("@/views/leaves/LeaveListView.vue"),
          meta: { title: "Nghỉ phép", permission: "leaves:view" },
        },
        {
          path: "leave-entitlements",
          name: "leave-entitlements",
          component: () => import("@/views/leaves/LeaveEntitlementView.vue"),
          meta: { title: "Số ngày phép", permission: "leaves:view" },
        },
        {
          path: "leave-reports",
          name: "leave-reports",
          redirect: { name: "leave-reports-canonical" },
          meta: { title: "Báo cáo nghỉ phép", permission: "leaves:view" },
        },
        // Bảo hiểm
        {
          path: "insurance",
          name: "insurance",
          component: () => import("@/views/insurance/InsuranceView.vue"),
          meta: { title: "Bảo hiểm BHXH", permission: "insurance:view" },
        },
        {
          path: "insurance/reports",
          name: "insurance-reports",
          component: () => import("@/views/insurance/InsuranceReportsView.vue"),
          meta: { title: "Báo cáo biến động BHXH", permission: "insurance:view" },
        },
        {
          path: "insurance/reports/:id",
          name: "insurance-report-detail",
          component: () =>
            import("@/views/insurance/InsuranceReportDetailView.vue"),
          meta: { title: "Chi tiết báo cáo BHXH", permission: "insurance:view" },
        },
        // Lương BHXH
        {
          path: "salary",
          name: "salary",
          component: () => import("@/views/salary/SalaryView.vue"),
          meta: { title: "Lương BHXH", permission: "insurance:view" },
        },
        {
          path: "salary/bhxh-adjustments",
          name: "salary-bhxh-adjustments",
          component: () => import("@/views/salary/BhxhAdjustmentsView.vue"),
          meta: { title: "Lịch sử điều chỉnh lương BHXH", permission: "insurance:view" },
        },
        // Khen thưởng & Kỷ luật
        {
          path: "rewards",
          name: "rewards",
          component: () => import("@/views/rewards/RewardsView.vue"),
          meta: { title: "Khen thưởng & Kỷ luật", permission: "rewards:view" },
        },
        // Đào tạo
        {
          path: "training",
          name: "training",
          component: () => import("@/views/training/TrainingView.vue"),
          meta: { title: "Đào tạo", permission: "training:view" },
        },
        // KPI
        {
          path: "performance",
          name: "performance",
          component: () => import("@/views/performance/PerformanceView.vue"),
          meta: { title: "Đánh giá KPI", permission: "performance:view" },
        },
        // Tuyển dụng
        {
          path: "recruitment",
          redirect: { name: "jr-list" },
        },
        {
          path: "recruitment/jr",
          name: "jr-list",
          component: () =>
            import("@/views/recruitment/components/JRListTab.vue"),
          meta: { title: "Yêu cầu tuyển dụng", permission: "recruitment:view" },
        },
        {
          path: "recruitment/jr/:id",
          name: "jr-detail",
          component: () => import("@/views/recruitment/JRDetailView.vue"),
          meta: { title: "Chi tiết yêu cầu tuyển dụng", permission: "recruitment:view" },
        },
        {
          path: "recruitment/postings",
          name: "posting-list",
          component: () =>
            import("@/views/recruitment/components/JobPostingTab.vue"),
          meta: { title: "Tin tuyển dụng", permission: "recruitment:view" },
        },
        {
          path: "recruitment/postings/:id",
          name: "posting-detail",
          component: () =>
            import("@/views/recruitment/JobPostingDetailView.vue"),
          meta: { title: "Chi tiết tin tuyển dụng", permission: "recruitment:view" },
        },
        {
          path: "recruitment/candidates",
          name: "candidate-list",
          component: () =>
            import("@/views/recruitment/components/CandidateListTab.vue"),
          meta: { title: "Ứng viên", permission: "recruitment:view" },
        },
        {
          path: "recruitment/candidates/:id",
          name: "candidate-detail",
          component: () =>
            import("@/views/recruitment/CandidateDetailView.vue"),
          meta: { title: "Chi tiết ứng viên", permission: "recruitment:view" },
        },
        {
          path: "recruitment/selection/:jr_id?",
          name: "selection",
          component: () => import("@/views/recruitment/KanbanPipelineView.vue"),
          meta: { title: "Tuyển chọn", permission: "recruitment:view" },
        },
        {
          path: "recruitment/applications/:id",
          name: "application-detail",
          component: () =>
            import("@/views/recruitment/ApplicationDetailView.vue"),
          meta: { title: "Chi tiết tuyển chọn", permission: "recruitment:view" },
        },
        {
          path: "recruitment/headcount",
          name: "headcount-plan",
          component: () =>
            import("@/views/recruitment/components/HeadcountPlanTab.vue"),
          meta: { title: "Kế hoạch nhân sự", permission: "recruitment:view" },
        },
        {
          path: "recruitment/legal",
          name: "legal-documents",
          redirect: { name: "employee-document-checklist-report" },
          meta: { title: "Báo cáo checklist hồ sơ lao động", permission: "recruitment:view" },
        },
        {
          path: "recruitment/settings",
          name: "recruitment-settings",
          component: () =>
            import("@/views/recruitment/components/EmailTemplateListTab.vue"),
          meta: { title: "Cài đặt tuyển dụng", permission: "recruitment:view" },
        },
        {
          path: "recruitment/reports",
          name: "recruitment-reports",
          redirect: { name: "recruitment-analytics" },
          meta: { title: "Báo cáo tuyển dụng", permission: "recruitment:view" },
        },
        // Báo cáo
        {
          path: "reports",
          name: "reports",
          component: () => import("@/views/reports/ReportView.vue"),
          meta: {
            title: "Tổng quan báo cáo",
            permission: "reports:view",
            anyPermissions: [
              "employees:view",
              "leaves:view",
              "insurance:view",
              "contracts:view",
              "recruitment:view",
              "training:view",
              "rewards:view",
              "performance:view",
              "reports:view",
            ],
          },
        },
        {
          path: "reports/dashboard",
          name: "dashboard-overview",
          component: () => import("@/views/reports/DashboardView.vue"),
          meta: {
            title: "Dashboard tổng quan",
            permission: "reports:view",
            anyPermissions: ["employees:view"],
          },
        },
        {
          path: "reports/hr",
          name: "hr-reports",
          component: () => import("@/views/reports/HRReportView.vue"),
          meta: {
            title: "Báo cáo nhân sự",
            permission: "reports:view",
            anyPermissions: ["employees:view"],
          },
        },
        {
          path: "reports/probation",
          name: "probation-analytics",
          component: () => import("@/views/reports/ProbationAnalyticsView.vue"),
          meta: {
            title: "Thử việc & onboarding",
            permission: "reports:view",
            anyPermissions: ["employees:view"],
          },
        },
        {
          path: "reports/leave",
          name: "leave-reports-canonical",
          component: () => import("@/views/leaves/LeaveReportView.vue"),
          meta: {
            title: "Báo cáo nghỉ phép",
            permission: "reports:view",
            anyPermissions: ["leaves:view"],
          },
        },
        {
          path: "reports/leave-analytics",
          name: "leave-analytics",
          redirect: { name: "leave-reports-canonical" },
          meta: {
            title: "Báo cáo nghỉ phép",
            permission: "reports:view",
            anyPermissions: ["leaves:view"],
          },
        },
        {
          path: "reports/insurance",
          name: "insurance-analytics",
          component: () => import("@/views/reports/InsuranceAnalyticsView.vue"),
          meta: {
            title: "Phân tích bảo hiểm",
            permission: "reports:view",
            anyPermissions: ["insurance:view"],
          },
        },
        {
          path: "reports/contracts",
          name: "contract-reports",
          component: () => import("@/views/reports/ContractReportView.vue"),
          meta: {
            title: "Báo cáo hợp đồng",
            permission: "reports:view",
            anyPermissions: ["contracts:view"],
          },
        },
        {
          path: "reports/recruitment",
          name: "recruitment-analytics",
          component: () => import("@/views/reports/RecruitmentAnalyticsView.vue"),
          meta: {
            title: "Báo cáo tuyển dụng",
            permission: "reports:view",
            anyPermissions: ["recruitment:view"],
          },
        },
        {
          path: "reports/employee-document-checklist",
          name: "employee-document-checklist-report",
          component: () => import("@/views/reports/EmployeeDocumentChecklistReportView.vue"),
          meta: {
            title: "Báo cáo checklist hồ sơ lao động",
            permission: "reports:view",
            anyPermissions: ["recruitment:view"],
          },
        },
        {
          path: "reports/training",
          name: "training-analytics",
          component: () => import("@/views/reports/TrainingAnalyticsView.vue"),
          meta: {
            title: "Báo cáo đào tạo",
            permission: "reports:view",
            anyPermissions: ["training:view"],
          },
        },
        {
          path: "reports/rewards",
          name: "rewards-analytics",
          component: () => import("@/views/reports/RewardsAnalyticsView.vue"),
          meta: {
            title: "Báo cáo khen thưởng & kỷ luật",
            permission: "reports:view",
            anyPermissions: ["rewards:view"],
          },
        },
        {
          path: "reports/performance",
          name: "performance-analytics",
          component: () => import("@/views/reports/PerformanceAnalyticsView.vue"),
          meta: {
            title: "Báo cáo hiệu suất / KPI",
            permission: "reports:view",
            anyPermissions: ["performance:view"],
          },
        },
        {
          path: "reports/export",
          name: "export-center",
          component: () => import("@/views/reports/ExportCenterView.vue"),
          meta: { title: "Xuất báo cáo", permission: "reports:view" },
        },
        {
          path: "data/import",
          name: "data-import",
          component: () => import("@/views/data/DataImportView.vue"),
          meta: {
            title: "Nhập dữ liệu",
            anyPermissions: [
              "org:edit",
              "employees:edit",
              "leaves:edit",
              "contracts:edit",
              "insurance:edit",
            ],
          },
        },
        // Danh mục
        {
          path: "catalog",
          name: "catalog",
          component: () => import("@/views/catalog/CatalogView.vue"),
          meta: {
            title: "Danh mục",
            permission: "catalog:view",
          },
        },
        {
          path: "catalog/administrative-units",
          name: "catalog-administrative-units",
          component: () =>
            import("@/views/catalog/AdministrativeUnitListView.vue"),
          meta: { title: "Danh mục hành chính", permission: "catalog:view" },
        },
        {
          path: "catalog/administrative-imports",
          name: "catalog-administrative-imports",
          component: () =>
            import("@/views/catalog/AdministrativeImportHistoryView.vue"),
          meta: { title: "Lịch sử import địa chỉ", permission: "catalog:view" },
        },
        {
          path: "catalog/education",
          name: "catalog-education",
          component: () => import("@/views/catalog/EducationCatalogView.vue"),
          meta: { title: "Danh mục học vấn", permission: "catalog:view" },
        },
        {
          path: "catalog/insurance",
          name: "catalog-insurance",
          component: () =>
            import("@/views/catalog/InsuranceFoundationView.vue"),
          meta: { title: "Cấu hình BHXH", permission: "insurance:view" },
        },
        {
          path: "catalog/other-business",
          name: "catalog-other-business",
          component: () =>
            import("@/views/catalog/OtherBusinessCatalogView.vue"),
          meta: { title: "Danh mục nghiệp vụ khác", permission: "catalog:view" },
        },
        {
          path: "catalog/bhyt-clinics",
          name: "catalog-bhyt-clinics",
          component: () => import("@/views/catalog/BhytClinicView.vue"),
          meta: { title: "Danh mục bệnh viện KCB", permission: "insurance:view" },
        },
        {
          path: "catalog/recruitment",
          name: "catalog-recruitment",
          component: () => import("@/views/catalog/RecruitmentCatalogView.vue"),
          meta: { title: "Danh mục tuyển dụng", permission: "recruitment:view" },
        },
        // Cài đặt
        {
          path: "settings",
          name: "settings",
          component: () => import("@/views/settings/SettingsView.vue"),
          meta: { title: "Cài đặt", permission: "settings:view" },
        },
        {
          path: "settings/notifications",
          name: "notification-settings",
          component: () => import("@/views/settings/NotificationSettingsView.vue"),
          meta: { title: "Cài đặt thông báo", permission: "settings:view" },
        },
        // Quản trị hệ thống — yêu cầu permission tương ứng
        {
          path: "admin/users",
          name: "admin-users",
          component: () => import("@/views/admin/UserListView.vue"),
          meta: { title: "Tài khoản người dùng", permission: "users:view" },
        },
        {
          path: "admin/roles",
          name: "admin-roles",
          component: () => import("@/views/admin/RoleListView.vue"),
          meta: { title: "Vai trò & Quyền", permission: "roles:view" },
        },
        {
          path: "admin/audit-logs",
          name: "admin-audit-logs",
          component: () => import("@/views/admin/AuditLogView.vue"),
          meta: { title: "Nhật ký hệ thống", permission: "audit_logs:view" },
        },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  const shouldAttemptRestore =
    !to.meta.public || Boolean(to.query.redirect);

  // M5 bootstrap: restore session đúng 1 lần qua HttpOnly cookie trước khi quyết định redirect.
  if (!auth.isAuthenticated && !auth.sessionResolved && shouldAttemptRestore) {
    await auth.tryRefresh();
  }

  // 1. Chưa đăng nhập → redirect login
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  // 2. Đã đăng nhập nhưng chưa load user data → fetch trước khi check permission
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.fetchMe();
    } catch (error) {
      if (isNetworkError(error)) {
        return false;
      }
      // Token hết hạn hoặc invalid → force logout
      auth.logout();
      return { name: "login", query: { redirect: to.fullPath } };
    }
  }

  // 3. Check permission nếu route yêu cầu
  const requiredPermission = to.meta.permission;
  if (requiredPermission && !auth.hasPermission(requiredPermission)) {
    if (to.name === "dashboard-overview") {
      return getDefaultAuthorizedRoute(auth);
    }
    return { name: "forbidden" };
  }

  const anyPermissions = to.meta.anyPermissions;
  if (anyPermissions && !anyPermissions.some((permission) => auth.hasPermission(permission))) {
    return { name: "forbidden" };
  }

  if (to.name === "org-department-detail") {
    const departmentId = Number(to.params.id);
    const scope = auth.user?.department_scopes?.org;
    if (Array.isArray(scope) && Number.isFinite(departmentId) && !scope.includes(departmentId)) {
      return { name: "forbidden" };
    }
  }

  if (
    Array.isArray(auth.user?.department_scopes?.org) &&
    (to.name === "org-job-titles" || to.name === "org-history")
  ) {
    return { name: "forbidden" };
  }

  // 4. Đã đăng nhập → không cho vào trang login
  if (to.name === "login" && auth.isAuthenticated) {
    return getDefaultAuthorizedRoute(auth);
  }
});

export default router;
