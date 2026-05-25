import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

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
      path: "/",
      component: () => import("@/components/layout/AppLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          redirect: "/dashboard",
        },
        {
          path: "dashboard",
          name: "dashboard",
          component: () => import("@/views/dashboard/DashboardView.vue"),
          meta: { title: "Dashboard", icon: "pi-home" },
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
          name: "recruitment",
          component: () => import("@/views/recruitment/RecruitmentView.vue"),
          meta: { title: "Tuyển dụng" },
        },
        {
          path: "recruitment/jr/:id",
          name: "jr-detail",
          component: () => import("@/views/recruitment/JRDetailView.vue"),
          meta: { title: "Chi tiết yêu cầu tuyển dụng" },
        },
        {
          path: "recruitment/postings/:id",
          name: "posting-detail",
          component: () =>
            import("@/views/recruitment/JobPostingDetailView.vue"),
          meta: { title: "Chi tiết tin tuyển dụng" },
        },
        {
          path: "recruitment/candidates/:id",
          name: "candidate-detail",
          component: () =>
            import("@/views/recruitment/CandidateDetailView.vue"),
          meta: { title: "Chi tiết ứng viên" },
        },
        {
          path: "recruitment/applications/:id",
          name: "application-detail",
          component: () =>
            import("@/views/recruitment/ApplicationDetailView.vue"),
          meta: { title: "Chi tiết tuyển chọn" },
        },
        // Báo cáo
        {
          path: "reports",
          name: "reports",
          component: () => import("@/views/reports/ReportView.vue"),
          meta: { title: "Báo cáo" },
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
          component: () =>
            import("@/views/catalog/RecruitmentCatalogView.vue"),
          meta: { title: "Danh mục tuyển dụng" },
        },
        // Cài đặt
        {
          path: "settings",
          name: "settings",
          component: () => import("@/views/settings/SettingsView.vue"),
          meta: { title: "Cài đặt" },
        },
        // Quản trị hệ thống
        {
          path: "admin/users",
          name: "admin-users",
          component: () => import("@/views/admin/UserListView.vue"),
          meta: { title: "Tài khoản người dùng" },
        },
        {
          path: "admin/roles",
          name: "admin-roles",
          component: () => import("@/views/admin/RoleListView.vue"),
          meta: { title: "Vai trò & Quyền" },
        },
        {
          path: "admin/audit-logs",
          name: "admin-audit-logs",
          component: () => import("@/views/admin/AuditLogView.vue"),
          meta: { title: "Nhật ký hệ thống" },
        },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.name === "login" && auth.isAuthenticated) {
    return { name: "dashboard" };
  }
});

export default router;
