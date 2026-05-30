import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

// Khai báo kiểu cho route meta
declare module "vue-router" {
  interface RouteMeta {
    title?: string
    public?: boolean
    permission?: string   // permission code cần có — VD: 'users:view'
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
          meta: { title: "Chức danh" },
        },
        {
          path: "org/departments",
          name: "org-departments",
          component: () => import("@/views/org/DepartmentListView.vue"),
          meta: { title: "Phòng / Ban" },
        },
        {
          path: "org/positions",
          name: "org-positions",
          component: () => import("@/views/org/PositionListView.vue"),
          meta: { title: "Vị trí công việc" },
        },
        {
          path: "org/history",
          name: "org-history",
          component: () => import("@/views/org/OrgHistoryView.vue"),
          meta: { title: "Lịch sử thay đổi" },
        },
        // Nhân sự
        {
          path: "employees",
          name: "employees",
          component: () => import("@/views/employees/EmployeeListView.vue"),
          meta: { title: "Danh sách nhân viên" },
        },
        {
          path: "employees/:id",
          name: "employee-detail",
          component: () => import("@/views/employees/EmployeeDetailView.vue"),
          meta: { title: "Hồ sơ nhân viên" },
        },
        // Probation reports
        {
          path: "employees/probation-reports",
          name: "employees-probation-reports",
          component: () => import("@/views/employees/ProbationReportView.vue"),
          meta: { title: "Báo cáo thử việc" },
        },
        // Onboarding
        {
          path: "employees/onboarding/tasks",
          name: "onboarding-tasks",
          component: () =>
            import("@/views/employees/OnboardingTaskConfigView.vue"),
          meta: { title: "Cấu hình task onboarding" },
        },
        {
          path: "employees/onboarding/:employee_id",
          name: "onboarding-detail",
          component: () => import("@/views/employees/OnboardingDetailView.vue"),
          meta: { title: "Chi tiết onboarding" },
        },
        {
          path: "employees/onboarding",
          name: "onboarding-list",
          component: () => import("@/views/employees/OnboardingListView.vue"),
          meta: { title: "Tiếp nhận nhân viên mới" },
        },
        // Nhắc nhở sự kiện
        {
          path: "reminders",
          name: "reminders",
          component: () => import("@/views/RemindersView.vue"),
          meta: { title: "Nhắc nhở sự kiện" },
        },
        // Hợp đồng
        {
          path: "contracts",
          name: "contracts",
          component: () => import("@/views/contracts/ContractListView.vue"),
          meta: { title: "Hợp đồng lao động" },
        },
        // Nghỉ phép
        {
          path: "leaves",
          name: "leaves",
          component: () => import("@/views/leaves/LeaveListView.vue"),
          meta: { title: "Nghỉ phép" },
        },
        {
          path: "leave-entitlements",
          name: "leave-entitlements",
          component: () => import("@/views/leaves/LeaveEntitlementView.vue"),
          meta: { title: "Số ngày phép" },
        },
        {
          path: "leave-reports",
          name: "leave-reports",
          component: () => import("@/views/leaves/LeaveReportView.vue"),
          meta: { title: "Báo cáo nghỉ phép" },
        },
        // Bảo hiểm
        {
          path: "insurance",
          name: "insurance",
          component: () => import("@/views/insurance/InsuranceView.vue"),
          meta: { title: "Bảo hiểm BHXH" },
        },
        {
          path: "insurance/reports",
          name: "insurance-reports",
          component: () => import("@/views/insurance/InsuranceReportsView.vue"),
          meta: { title: "Báo cáo biến động BHXH" },
        },
        {
          path: "insurance/reports/:id",
          name: "insurance-report-detail",
          component: () =>
            import("@/views/insurance/InsuranceReportDetailView.vue"),
          meta: { title: "Chi tiết báo cáo BHXH" },
        },
        // Lương BHXH
        {
          path: "salary",
          name: "salary",
          component: () => import("@/views/salary/SalaryView.vue"),
          meta: { title: "Lương BHXH" },
        },
        {
          path: "salary/bhxh-adjustments",
          name: "salary-bhxh-adjustments",
          component: () => import("@/views/salary/BhxhAdjustmentsView.vue"),
          meta: { title: "Lịch sử điều chỉnh lương BHXH" },
        },
        // Khen thưởng & Kỷ luật
        {
          path: "rewards",
          name: "rewards",
          component: () => import("@/views/rewards/RewardsView.vue"),
          meta: { title: "Khen thưởng & Kỷ luật" },
        },
        // Đào tạo
        {
          path: "training",
          name: "training",
          component: () => import("@/views/training/TrainingView.vue"),
          meta: { title: "Đào tạo" },
        },
        // KPI
        {
          path: "performance",
          name: "performance",
          component: () => import("@/views/performance/PerformanceView.vue"),
          meta: { title: "Đánh giá KPI" },
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
          meta: { title: "Yêu cầu tuyển dụng" },
        },
        {
          path: "recruitment/jr/:id",
          name: "jr-detail",
          component: () => import("@/views/recruitment/JRDetailView.vue"),
          meta: { title: "Chi tiết yêu cầu tuyển dụng" },
        },
        {
          path: "recruitment/postings",
          name: "posting-list",
          component: () =>
            import("@/views/recruitment/components/JobPostingTab.vue"),
          meta: { title: "Tin tuyển dụng" },
        },
        {
          path: "recruitment/postings/:id",
          name: "posting-detail",
          component: () =>
            import("@/views/recruitment/JobPostingDetailView.vue"),
          meta: { title: "Chi tiết tin tuyển dụng" },
        },
        {
          path: "recruitment/candidates",
          name: "candidate-list",
          component: () =>
            import("@/views/recruitment/components/CandidateListTab.vue"),
          meta: { title: "Ứng viên" },
        },
        {
          path: "recruitment/candidates/:id",
          name: "candidate-detail",
          component: () =>
            import("@/views/recruitment/CandidateDetailView.vue"),
          meta: { title: "Chi tiết ứng viên" },
        },
        {
          path: "recruitment/selection/:jr_id?",
          name: "selection",
          component: () => import("@/views/recruitment/KanbanPipelineView.vue"),
          meta: { title: "Tuyển chọn" },
        },
        {
          path: "recruitment/applications/:id",
          name: "application-detail",
          component: () =>
            import("@/views/recruitment/ApplicationDetailView.vue"),
          meta: { title: "Chi tiết tuyển chọn" },
        },
        {
          path: "recruitment/headcount",
          name: "headcount-plan",
          component: () =>
            import("@/views/recruitment/components/HeadcountPlanTab.vue"),
          meta: { title: "Kế hoạch nhân sự" },
        },
        {
          path: "recruitment/legal",
          name: "legal-documents",
          component: () =>
            import("@/views/recruitment/components/DocumentChecklistSummaryTab.vue"),
          meta: { title: "Hồ sơ pháp lý" },
        },
        {
          path: "recruitment/settings",
          name: "recruitment-settings",
          component: () =>
            import("@/views/recruitment/components/EmailTemplateListTab.vue"),
          meta: { title: "Cài đặt tuyển dụng" },
        },
        {
          path: "recruitment/reports",
          name: "recruitment-reports",
          component: () =>
            import("@/views/recruitment/RecruitmentReportView.vue"),
          meta: { title: "Báo cáo tuyển dụng" },
        },
        // Báo cáo
        {
          path: "reports",
          name: "reports",
          component: () => import("@/views/reports/ReportView.vue"),
          meta: { title: "Báo cáo" },
        },
        {
          path: "reports/dashboard",
          name: "dashboard-overview",
          component: () => import("@/views/reports/DashboardView.vue"),
          meta: { title: "Dashboard tổng quan" },
        },
        {
          path: "reports/hr",
          name: "hr-reports",
          component: () => import("@/views/reports/HRReportView.vue"),
          meta: { title: "Báo cáo nhân sự" },
        },
        {
          path: "reports/leave-analytics",
          name: "leave-analytics",
          component: () => import("@/views/reports/LeaveAnalyticsView.vue"),
          meta: { title: "Phân tích nghỉ phép" },
        },
        {
          path: "reports/insurance",
          name: "insurance-analytics",
          component: () => import("@/views/reports/InsuranceAnalyticsView.vue"),
          meta: { title: "Báo cáo Bảo hiểm", permission: "insurance:read" },
        },
        {
          path: "reports/contracts",
          name: "contract-reports",
          component: () => import("@/views/reports/ContractReportView.vue"),
          meta: { title: "Báo cáo Hợp đồng", permission: "employees:read" },
        },
        {
          path: "reports/export",
          name: "export-center",
          component: () => import("@/views/reports/ExportCenterView.vue"),
          meta: { title: "Xuất báo cáo" },
        },
        {
          path: "data/import",
          name: "data-import",
          component: () => import("@/views/data/DataImportView.vue"),
          meta: { title: "Nhập dữ liệu" },
        },
        // Danh mục
        {
          path: "catalog",
          name: "catalog",
          component: () => import("@/views/catalog/CatalogView.vue"),
          meta: { title: "Danh mục" },
        },
        {
          path: "catalog/administrative-units",
          name: "catalog-administrative-units",
          component: () =>
            import("@/views/catalog/AdministrativeUnitListView.vue"),
          meta: { title: "Danh mục hành chính" },
        },
        {
          path: "catalog/administrative-imports",
          name: "catalog-administrative-imports",
          component: () =>
            import("@/views/catalog/AdministrativeImportHistoryView.vue"),
          meta: { title: "Lịch sử import địa chỉ" },
        },
        {
          path: "catalog/education",
          name: "catalog-education",
          component: () => import("@/views/catalog/EducationCatalogView.vue"),
          meta: { title: "Danh mục học vấn" },
        },
        {
          path: "catalog/insurance",
          name: "catalog-insurance",
          component: () =>
            import("@/views/catalog/InsuranceFoundationView.vue"),
          meta: { title: "Cấu hình BHXH" },
        },
        {
          path: "catalog/other-business",
          name: "catalog-other-business",
          component: () =>
            import("@/views/catalog/OtherBusinessCatalogView.vue"),
          meta: { title: "Danh mục nghiệp vụ khác" },
        },
        {
          path: "catalog/bhyt-clinics",
          name: "catalog-bhyt-clinics",
          component: () => import("@/views/catalog/BhytClinicView.vue"),
          meta: { title: "Danh mục bệnh viện KCB" },
        },
        {
          path: "catalog/recruitment",
          name: "catalog-recruitment",
          component: () => import("@/views/catalog/RecruitmentCatalogView.vue"),
          meta: { title: "Danh mục tuyển dụng" },
        },
        // Cài đặt
        {
          path: "settings",
          name: "settings",
          component: () => import("@/views/settings/SettingsView.vue"),
          meta: { title: "Cài đặt" },
        },
        {
          path: "settings/notifications",
          name: "notification-settings",
          component: () => import("@/views/settings/NotificationSettingsView.vue"),
          meta: { title: "Cài đặt thông báo" },
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
    } catch {
      // Token hết hạn hoặc invalid → force logout
      auth.logout();
      return { name: "login", query: { redirect: to.fullPath } };
    }
  }

  // 3. Check permission nếu route yêu cầu
  const requiredPermission = to.meta.permission;
  if (requiredPermission && !auth.hasPermission(requiredPermission)) {
    return { name: "forbidden" };
  }

  // 4. Đã đăng nhập → không cho vào trang login
  if (to.name === "login" && auth.isAuthenticated) {
    return { name: "dashboard-overview" };
  }
});

export default router;
