<template>
  <nav>
    <template v-for="item in menu" :key="item.label">
      <!-- Section header -->
      <div v-if="item.section" class="layout-menu-section-label">
        {{ item.label }}
      </div>

      <!-- Menu item with children -->
      <div v-else-if="item.items" class="layout-menu-item">
        <div class="menu-toggle" @click="toggleGroup(item.label)">
          <i :class="['pi menu-icon', item.icon]" />
          <span class="menu-label" v-show="!collapsed">{{ item.label }}</span>
          <i
            v-show="!collapsed"
            :class="[
              'pi menu-chevron',
              openGroups.has(item.label)
                ? 'pi-chevron-down'
                : 'pi-chevron-right',
            ]"
          />
        </div>
        <ul
          v-show="openGroups.has(item.label) && !collapsed"
          class="layout-menu submenu"
        >
          <li
            v-for="child in item.items"
            :key="child.to"
            class="layout-menu-item"
          >
            <RouterLink :to="child.to">
              <i
                :class="['pi menu-icon', child.icon ?? 'pi-minus']"
                style="font-size: 0.75rem"
              />
              <span class="menu-label">{{ child.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </div>

      <!-- Single menu item -->
      <div v-else class="layout-menu-item">
        <RouterLink :to="item.to!">
          <i :class="['pi menu-icon', item.icon]" />
          <span class="menu-label" v-show="!collapsed">{{ item.label }}</span>
          <span
            v-if="item.to === '/reminders' && reminderBadge > 0 && !collapsed"
            class="menu-badge"
            >{{ reminderBadge }}</span
          >
        </RouterLink>
      </div>
    </template>
  </nav>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import reminderService from "@/services/reminderService";

defineProps<{ collapsed: boolean }>();

interface MenuItem {
  to?: string;
  label: string;
  icon?: string;
  section?: boolean;
  items?: { to: string; label: string; icon?: string }[];
}

const openGroups = ref<Set<string>>(
  new Set(["Cơ cấu tổ chức", "Nhân sự", "Tuyển dụng", "Báo cáo", "Danh mục"]),
);
const reminderBadge = ref(0);

onMounted(async () => {
  try {
    const res = await reminderService.getReminders(7);
    reminderBadge.value = res.data.total;
  } catch {
    /* sidebar badge không block UI */
  }
});

function toggleGroup(label: string) {
  if (openGroups.value.has(label)) {
    openGroups.value.delete(label);
  } else {
    openGroups.value.add(label);
  }
}

const menu: MenuItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: "pi-home" },
  { section: true, label: "Quản lý" },
  {
    label: "Cơ cấu tổ chức",
    icon: "pi-sitemap",
    items: [
      { to: "/org/departments", label: "Phòng / Ban" },
      { to: "/org/job-titles", label: "Chức danh" },
      { to: "/org/positions", label: "Vị trí công việc" },
      { to: "/org/history", label: "Lịch sử thay đổi", icon: "pi-history" },
    ],
  },
  {
    label: "Nhân sự",
    icon: "pi-users",
    items: [
      { to: "/employees", label: "Danh sách nhân viên" },
      {
        to: "/employees/onboarding",
        label: "Tiếp nhận nhân viên mới",
        icon: "pi-clipboard",
      },
      {
        to: "/employees/probation-reports",
        label: "Báo cáo thử việc",
        icon: "pi-chart-bar",
      },
    ],
  },
  { to: "/reminders", label: "Nhắc nhở", icon: "pi-bell" },
  { to: "/contracts", label: "Hợp đồng", icon: "pi-file-edit" },
  {
    label: "Nghỉ phép",
    icon: "pi-calendar",
    items: [
      {
        to: "/leave-entitlements",
        label: "Số ngày phép",
        icon: "pi-chart-bar",
      },
      { to: "/leaves", label: "Ghi nhận nghỉ phép", icon: "pi-calendar-times" },
      {
        to: "/leave-reports",
        label: "Báo cáo nghỉ phép",
        icon: "pi-file-excel",
      },
    ],
  },
  {
    label: "Bảo hiểm BHXH",
    icon: "pi-shield",
    items: [
      { to: "/insurance", label: "Hồ sơ & Chính sách", icon: "pi-id-card" },
      {
        to: "/insurance/reports",
        label: "Báo cáo biến động",
        icon: "pi-file-excel",
      },
    ],
  },
  {
    label: "Lương BHXH",
    icon: "pi-dollar",
    items: [
      { to: "/salary", label: "Mức lương BHXH", icon: "pi-list" },
      {
        to: "/salary/bhxh-adjustments",
        label: "Lịch sử điều chỉnh",
        icon: "pi-history",
      },
    ],
  },
  { to: "/rewards", label: "Khen thưởng & Kỷ luật", icon: "pi-star" },
  { to: "/training", label: "Đào tạo", icon: "pi-graduation-cap" },
  { to: "/performance", label: "Đánh giá KPI", icon: "pi-chart-bar" },
  {
    label: "Tuyển dụng",
    icon: "pi-briefcase",
    items: [
      { to: "/recruitment/jr", label: "Yêu cầu tuyển dụng" },
      { to: "/recruitment/postings", label: "Tin tuyển dụng" },
      { to: "/recruitment/candidates", label: "Ứng viên" },
      { to: "/recruitment/selection", label: "Tuyển chọn" },
      { to: "/recruitment/headcount", label: "Kế hoạch nhân sự" },
      { to: "/recruitment/legal", label: "Hồ sơ pháp lý" },
      { to: "/recruitment/settings", label: "Cài đặt tuyển dụng" },
      { to: "/recruitment/reports", label: "Báo cáo tuyển dụng" },
    ],
  },
  { section: true, label: "Phân tích" },
  {
    label: "Báo cáo",
    icon: "pi-chart-pie",
    items: [
      {
        to: "/reports/dashboard",
        label: "Dashboard nhân sự",
        icon: "pi-chart-pie",
      },
      {
        to: "/reports/hr",
        label: "Báo cáo nhân sự",
        icon: "pi-users",
      },
      { to: "/reports", label: "Tổng quan báo cáo", icon: "pi-folder-open" },
    ],
  },
  { section: true, label: "Hệ thống" },
  {
    label: "Danh mục",
    icon: "pi-list",
    items: [
      { to: "/catalog", label: "Tổng quan danh mục", icon: "pi-th-large" },
      {
        to: "/catalog/insurance",
        label: "Cấu hình BHXH",
        icon: "pi-sliders-h",
      },
      {
        to: "/catalog/administrative-units",
        label: "Danh mục hành chính",
        icon: "pi-map",
      },
      {
        to: "/catalog/education",
        label: "Danh mục học vấn",
        icon: "pi-graduation-cap",
      },
      {
        to: "/catalog/other-business",
        label: "Danh mục nghiệp vụ khác",
        icon: "pi-briefcase",
      },
      {
        to: "/catalog/recruitment",
        label: "Danh mục tuyển dụng",
        icon: "pi-sitemap",
      },
      {
        to: "/catalog/bhyt-clinics",
        label: "Danh mục bệnh viện KCB",
        icon: "pi-heart",
      },
      {
        to: "/catalog/administrative-imports",
        label: "Lịch sử import",
        icon: "pi-download",
      },
    ],
  },
  { to: "/settings", label: "Cài đặt", icon: "pi-cog" },
  { section: true, label: "Quản trị" },
  { to: "/admin/users", label: "Tài khoản người dùng", icon: "pi-user-edit" },
  { to: "/admin/roles", label: "Vai trò & Quyền", icon: "pi-shield" },
  { to: "/admin/audit-logs", label: "Nhật ký hệ thống", icon: "pi-list" },
];
</script>
