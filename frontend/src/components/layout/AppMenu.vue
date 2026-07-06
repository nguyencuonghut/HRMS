<template>
  <nav>
    <template v-for="item in filteredMenu" :key="item.label">
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
            <RouterLink :to="child.to" :class="{ 'router-link-active': isRouteActive(child.to) }">
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
        <RouterLink :to="item.to!" :class="{ 'router-link-active': isRouteActive(item.to!) }">
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
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { usePermissionGate } from "@/composables/usePermissionGate";
import reminderService from "@/services/reminderService";

defineProps<{ collapsed: boolean }>();

interface MenuChildItem {
  to: string;
  label: string;
  icon?: string;
  permission?: string;
  anyPermissions?: string[];
}

interface MenuItem {
  to?: string;
  label: string;
  icon?: string;
  section?: boolean;
  permission?: string;
  anyPermissions?: string[];
  items?: MenuChildItem[];
}

const route = useRoute();
const permissionGate = usePermissionGate();

const openGroups = ref<Set<string>>(
  new Set(["Cơ cấu tổ chức", "Nhân sự", "Tuyển dụng", "Báo cáo", "Danh mục"]),
);
const reminderBadge = ref(0);
const canLoadReminderBadge = computed(() => permissionGate.canAccessRoute("/reminders"));
const scopedOrgHiddenRoutes = new Set<string>(["/org/job-titles", "/org/history"]);

onMounted(async () => {
  if (!canLoadReminderBadge.value) {
    reminderBadge.value = 0;
    return;
  }
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

function canAccessChild(item: MenuChildItem): boolean {
  if (permissionGate.isDepartmentScoped("org") && scopedOrgHiddenRoutes.has(item.to)) {
    return false;
  }
  if (!permissionGate.canAccess(item)) {
    return false;
  }
  return permissionGate.canAccessRoute(item.to);
}

function canAccessItem(item: MenuItem): boolean {
  if (!permissionGate.canAccess(item)) {
    return false;
  }
  if (item.to) {
    return permissionGate.canAccessRoute(item.to);
  }
  if (item.items) {
    return item.items.some((child) => canAccessChild(child));
  }
  return true;
}

function flattenMenuRoutes(items: MenuItem[]): string[] {
  return items.flatMap((item) => {
    if (!canAccessItem(item)) return [];
    const own = item.to ? [item.to] : [];
    const children = item.items
      ? item.items.filter((child) => canAccessChild(child)).map((child) => child.to)
      : [];
    return [...own, ...children];
  });
}

const activeMenuTarget = computed(() => {
  const currentPath = route.path;
  const candidates = flattenMenuRoutes(filteredMenu.value).filter(
    (target) => currentPath === target || currentPath.startsWith(`${target}/`),
  );
  if (candidates.length === 0) return null;
  return candidates.sort((a, b) => b.length - a.length)[0];
});

function isRouteActive(target: string): boolean {
  return activeMenuTarget.value === target;
}

const menu: MenuItem[] = [
  { to: "/reports/dashboard", label: "Dashboard tổng quan", icon: "pi-home" },
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
        label: "Xem báo cáo thử việc",
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
        label: "Xem báo cáo nghỉ phép",
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
        label: "Kỳ báo cáo BHXH",
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
      { to: "/recruitment/settings", label: "Cài đặt tuyển dụng" },
      { to: "/recruitment/reports", label: "Xem báo cáo tuyển dụng" },
      { to: "/recruitment/legal", label: "Xem báo cáo checklist hồ sơ LĐ" },
    ],
  },
  { section: true, label: "Phân tích" },
  {
    label: "Báo cáo",
    icon: "pi-chart-pie",
    items: [
      { to: "/reports", label: "Tổng quan báo cáo", icon: "pi-folder-open" },
      {
        to: "/reports/dashboard",
        label: "Dashboard tổng quan",
        icon: "pi-chart-pie",
      },
      {
        to: "/reports/hr",
        label: "Nhân sự",
        icon: "pi-users",
      },
      {
        to: "/reports/probation",
        label: "Thử việc & onboarding",
        icon: "pi-user-plus",
      },
      {
        to: "/reports/leave",
        label: "Nghỉ phép",
        icon: "pi-chart-bar",
      },
      {
        to: "/reports/insurance",
        label: "Bảo hiểm",
        icon: "pi-shield",
      },
      {
        to: "/reports/contracts",
        label: "Hợp đồng",
        icon: "pi-file",
      },
      {
        to: "/reports/recruitment",
        label: "Tuyển dụng",
        icon: "pi-briefcase",
      },
      {
        to: "/reports/employee-document-checklist",
        label: "Checklist hồ sơ lao động",
        icon: "pi-id-card",
      },
      {
        to: "/reports/training",
        label: "Đào tạo",
        icon: "pi-graduation-cap",
      },
      {
        to: "/reports/rewards",
        label: "Khen thưởng & Kỷ luật",
        icon: "pi-star",
      },
      {
        to: "/reports/performance",
        label: "Hiệu suất / KPI",
        icon: "pi-chart-bar",
      },
      {
        to: "/reports/export",
        label: "Xuất báo cáo",
        icon: "pi-file-export",
      },
    ],
  },
  { section: true, label: "Nhập/Xuất" },
  {
    to: "/data/import",
    label: "Nhập dữ liệu",
    icon: "pi-upload",
    permission: "data_import:view",
  },
  {
    to: "/data/export",
    label: "Xuất dữ liệu",
    icon: "pi-download",
    permission: "employees:export",
  },
  { section: true, label: "Hệ thống" },
  {
    label: "Danh mục",
    icon: "pi-list",
    items: [
      {
        to: "/catalog",
        label: "Tổng quan danh mục",
        icon: "pi-th-large",
        permission: "catalog:view",
      },
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
  {
    label: "Cài đặt",
    icon: "pi-cog",
    items: [
      { to: "/settings", label: "Cài đặt hệ thống", icon: "pi-sliders-h" },
      { to: "/settings/notifications", label: "Thông báo email", icon: "pi-bell" },
    ],
  },
  { section: true, label: "Quản trị" },
  { to: "/admin/users", label: "Tài khoản người dùng", icon: "pi-user-edit" },
  { to: "/admin/roles", label: "Vai trò & Quyền", icon: "pi-shield" },
  { to: "/admin/audit-logs", label: "Nhật ký hệ thống", icon: "pi-list" },
];

const filteredMenu = computed(() => {
  const result: MenuItem[] = [];
  let pendingSection: MenuItem | null = null;

  for (const item of menu) {
    if (item.section) {
      pendingSection = item;
      continue;
    }

    let candidate: MenuItem = item;
    if (item.items) {
      if (!permissionGate.canAccess(item)) {
        continue;
      }
      const visibleChildren = item.items.filter((child) => canAccessChild(child));
      if (visibleChildren.length === 0) {
        continue;
      }
      candidate = {
        ...item,
        items: visibleChildren,
      };
    } else if (!canAccessItem(item)) {
      continue;
    }

    if (pendingSection) {
      result.push(pendingSection);
      pendingSection = null;
    }
    result.push(candidate);
  }

  return result;
});
</script>
