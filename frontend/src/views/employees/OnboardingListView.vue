<template>
  <div class="ob-list">
    <!-- Breadcrumb -->
    <nav class="ob-breadcrumb">
      <RouterLink to="/employees">Nhân viên</RouterLink>
      <i class="pi pi-chevron-right" />
      <span>Tiếp nhận nhân viên mới</span>
    </nav>

    <!-- Filter + action bar -->
    <div class="toolbar">
      <Select
        v-model="filterStatus"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        class="toolbar-filter"
        @change="loadList"
      />
      <Select
        v-model="filterDeptId"
        :options="departments"
        option-label="name"
        option-value="id"
        placeholder="Phòng ban"
        show-clear
        class="toolbar-filter"
        @change="loadList"
      />
      <InputNumber
        v-model="filterDaysUntil"
        :min="0"
        :use-grouping="false"
        placeholder="Còn ≤ N ngày thử việc"
        class="toolbar-filter"
        @keydown.enter="loadList"
        @blur="loadList"
      />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        v-tooltip.top="'Làm mới'"
        :loading="loading"
        @click="resetFilters"
      />
      <div style="flex: 1" />
      <Button
        label="Tạo checklist thủ công"
        icon="pi pi-plus"
        @click="showCreateDialog = true"
      />
      <Button
        label="Cấu hình task"
        icon="pi pi-cog"
        severity="secondary"
        outlined
        @click="$router.push('/employees/onboarding/tasks')"
      />
    </div>

    <!-- Table -->
    <div class="ob-card">
      <DataTable
        :value="items"
        :loading="loading"
        striped-rows
        size="small"
        lazy
        :total-records="total"
        :rows="pageSize"
        :first="(page - 1) * pageSize"
        paginator
        :rows-per-page-options="[10, 20, 50]"
        @page="onPage"
      >
        <template #empty>
          <div class="ob-empty">Không có checklist nào</div>
        </template>

        <Column header="Nhân viên" min-header-width="160px">
          <template #body="{ data }">
            <div class="ob-emp-cell">
              <span class="ob-emp-name">{{ data.employee_name }}</span>
              <Tag :value="data.employee_code" severity="secondary" style="font-size: 0.7rem" />
            </div>
          </template>
        </Column>

        <Column field="department_name" header="Phòng ban" style="width: 160px">
          <template #body="{ data }">{{ data.department_name ?? '—' }}</template>
        </Column>

        <Column header="Ngày vào làm" style="width: 120px">
          <template #body="{ data }">{{ fmtDate(data.start_date) }}</template>
        </Column>

        <Column header="Buddy" style="width: 140px">
          <template #body="{ data }">{{ data.buddy_name ?? '—' }}</template>
        </Column>

        <Column header="Tiến độ" style="width: 180px">
          <template #body="{ data }">
            <div class="ob-progress-cell">
              <ProgressBar
                :value="data.completion_pct"
                style="height: 8px"
                :class="data.completion_pct === 100 ? 'ob-progress-done' : ''"
              />
              <span class="ob-progress-label">{{ data.done_items }}/{{ data.total_items }}</span>
            </div>
          </template>
        </Column>

        <Column header="Quá hạn" style="width: 90px; text-align: center">
          <template #body="{ data }">
            <Badge
              v-if="data.overdue_items > 0"
              :value="String(data.overdue_items)"
              severity="danger"
            />
            <span v-else class="ob-muted">—</span>
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 130px">
          <template #body="{ data }">
            <Tag
              :value="statusLabel(data.status)"
              :severity="statusSeverity(data.status)"
            />
          </template>
        </Column>

        <Column header="Thao tác" style="width: 110px">
          <template #body="{ data }">
            <Button
              label="Chi tiết"
              size="small"
              text
              icon="pi pi-eye"
              @click="$router.push(`/employees/onboarding/${data.employee_id}`)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create Dialog -->
    <OnboardingCreateDialog
      v-if="showCreateDialog"
      @close="showCreateDialog = false"
      @created="onCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { onboardingChecklistService, type OnboardingChecklistListItem } from '@/services/onboardingService'
import api from '@/services/api'
import OnboardingCreateDialog from './OnboardingCreateDialog.vue'

const toast = useToast()

const items = ref<OnboardingChecklistListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const filterStatus = ref<string | null>(null)
const filterDeptId = ref<number | null>(null)
const filterDaysUntil = ref<number | null>(null)
const showCreateDialog = ref(false)

const departments = ref<{ id: number; name: string }[]>([])

const statusOptions = [
  { label: 'Tất cả', value: null },
  { label: 'Đang thực hiện', value: 'in_progress' },
  { label: 'Hoàn thành', value: 'completed' },
  { label: 'Đã hủy', value: 'cancelled' },
]

onMounted(async () => {
  try {
    const r = await api.get('/departments', { params: { page_size: 200 } })
    const data = r.data
    departments.value = Array.isArray(data) ? data : (data.items ?? [])
  } catch { /* sidebar error không block */ }
  await loadList()
})

async function loadList() {
  loading.value = true
  try {
    const res = await onboardingChecklistService.list({
      status: filterStatus.value ?? undefined,
      department_id: filterDeptId.value ?? undefined,
      days_until_completion: filterDaysUntil.value ?? undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = res.items
    total.value = res.total
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách onboarding', life: 4000 })
  } finally {
    loading.value = false
  }
}

function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  void loadList()
}

function resetFilters() {
  filterStatus.value = null
  filterDeptId.value = null
  filterDaysUntil.value = null
  page.value = 1
  void loadList()
}

function onCreated() {
  showCreateDialog.value = false
  void loadList()
}

function fmtDate(s: string): string {
  return new Date(s).toLocaleDateString('vi-VN')
}

function statusLabel(st: string): string {
  if (st === 'in_progress') return 'Đang thực hiện'
  if (st === 'completed') return 'Hoàn thành'
  if (st === 'cancelled') return 'Đã hủy'
  return st
}

function statusSeverity(st: string): string {
  if (st === 'in_progress') return 'warn'
  if (st === 'completed') return 'success'
  if (st === 'cancelled') return 'danger'
  return 'secondary'
}
</script>
