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
            :class="['pi menu-chevron', openGroups.has(item.label) ? 'pi-chevron-down' : 'pi-chevron-right']"
          />
        </div>
        <ul v-show="openGroups.has(item.label) && !collapsed" class="layout-menu submenu">
          <li v-for="child in item.items" :key="child.to" class="layout-menu-item">
            <RouterLink :to="child.to">
              <i :class="['pi menu-icon', child.icon ?? 'pi-minus']" style="font-size: 0.75rem" />
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
        </RouterLink>
      </div>
    </template>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ collapsed: boolean }>()

interface MenuItem {
  to?: string
  label: string
  icon?: string
  section?: boolean
  items?: { to: string; label: string; icon?: string }[]
}

const openGroups = ref<Set<string>>(new Set(['Cơ cấu tổ chức']))

function toggleGroup(label: string) {
  if (openGroups.value.has(label)) {
    openGroups.value.delete(label)
  } else {
    openGroups.value.add(label)
  }
}

const menu: MenuItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: 'pi-home' },
  { section: true, label: 'Quản lý' },
  {
    label: 'Cơ cấu tổ chức',
    icon: 'pi-sitemap',
    items: [
      { to: '/org/departments', label: 'Phòng / Ban' },
      { to: '/org/job-titles',  label: 'Chức danh' },
      { to: '/org/positions',   label: 'Vị trí công việc' },
      { to: '/org/history',     label: 'Lịch sử thay đổi', icon: 'pi-history' },
    ],
  },
  { to: '/employees', label: 'Nhân sự', icon: 'pi-users' },
  { to: '/contracts', label: 'Hợp đồng', icon: 'pi-file-edit' },
  { to: '/leaves', label: 'Nghỉ phép', icon: 'pi-calendar' },
  { to: '/insurance', label: 'Bảo hiểm BHXH', icon: 'pi-shield' },
  { to: '/salary', label: 'Lương BHXH', icon: 'pi-dollar' },
  { to: '/rewards', label: 'Khen thưởng & Kỷ luật', icon: 'pi-star' },
  { to: '/training', label: 'Đào tạo', icon: 'pi-graduation-cap' },
  { to: '/performance', label: 'Đánh giá KPI', icon: 'pi-chart-bar' },
  { section: true, label: 'Phân tích' },
  { to: '/reports', label: 'Báo cáo', icon: 'pi-chart-pie' },
  { section: true, label: 'Hệ thống' },
  { to: '/catalog', label: 'Danh mục', icon: 'pi-list' },
  { to: '/settings', label: 'Cài đặt', icon: 'pi-cog' },
  { section: true, label: 'Quản trị' },
  { to: '/admin/users', label: 'Tài khoản người dùng', icon: 'pi-user-edit' },
]
</script>

