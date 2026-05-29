<template>
  <div class="page-container">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2 class="page-title">Nhắc nhở sự kiện nhân sự</h2>
        <p style="margin:0; color:var(--l-text-muted); font-size:0.875rem;">
          Các sự kiện sắp đến trong {{ daysParam }} ngày tới
        </p>
      </div>
      <div style="display:flex; gap:0.75rem; align-items:center;">
        <Select
          v-model="daysParam"
          :options="daysOptions"
          option-label="label"
          option-value="value"
          style="min-width:140px;"
          @change="load"
        />
        <Select
          v-model="typeFilter"
          :options="typeOptions"
          option-label="label"
          option-value="value"
          filter
          show-clear
          placeholder="Lọc loại sự kiện"
          style="min-width:180px;"
        />
        <Button icon="pi pi-refresh" text rounded :loading="loading" aria-label="Làm mới" @click="load" v-tooltip.top="'Làm mới'" />
      </div>
    </div>

    <!-- Summary cards -->
    <div class="reminder-cards">
      <div class="reminder-card">
        <span class="reminder-card-icon">🎂</span>
        <div class="reminder-card-body">
          <div class="reminder-card-count">{{ data?.birthday.length ?? 0 }}</div>
          <div class="reminder-card-label">Sinh nhật</div>
        </div>
      </div>
      <div class="reminder-card">
        <span class="reminder-card-icon">⭐</span>
        <div class="reminder-card-body">
          <div class="reminder-card-count">{{ data?.anniversary.length ?? 0 }}</div>
          <div class="reminder-card-label">Thâm niên</div>
        </div>
      </div>
      <div class="reminder-card">
        <span class="reminder-card-icon">📋</span>
        <div class="reminder-card-body">
          <div class="reminder-card-count">{{ data?.probation_end.length ?? 0 }}</div>
          <div class="reminder-card-label">Hết thử việc</div>
        </div>
      </div>
      <div class="reminder-card reminder-card--warning">
        <span class="reminder-card-icon">📄</span>
        <div class="reminder-card-body">
          <div class="reminder-card-count">{{ data?.contract_expiry.length ?? 0 }}</div>
          <div class="reminder-card-label">HĐ sắp hết hạn</div>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="section-card">
      <DataTable
        :value="filteredItems"
        :loading="loading"
        sort-field="days_until"
        :sort-order="1"
        row-hover
        striped-rows
        @row-click="(e) => goToEmployee(e.data)"
        style="cursor:pointer;"
      >
        <template #empty>
          <div style="text-align:center; padding:2rem; color:var(--l-text-muted);">
            Không có sự kiện nào trong {{ daysParam }} ngày tới
          </div>
        </template>

        <Column field="event_type" header="Loại" style="width:180px;">
          <template #body="{ data: row }">
            <span>{{ EVENT_TYPE_ICONS[row.event_type as EventType] }} {{ EVENT_TYPE_LABELS[row.event_type as EventType] }}</span>
            <span v-if="row.event_type === 'anniversary' && row.extra?.years" style="margin-left:0.4rem; font-size:0.8rem; color:var(--l-text-muted);">
              ({{ row.extra.years }} năm)
            </span>
            <div v-if="row.event_type === 'contract_expiry' && row.extra?.contract_number" style="font-size:0.8rem; color:var(--l-text-muted);">
              {{ row.extra.contract_number }}
            </div>
          </template>
        </Column>

        <Column field="employee_name" header="Nhân viên" sortable>
          <template #body="{ data: row }">
            <div style="font-weight:500;">{{ row.employee_name }}</div>
            <div style="font-size:0.8rem; color:var(--l-text-muted);">{{ row.employee_code }}</div>
          </template>
        </Column>

        <Column field="department" header="Phòng ban" sortable>
          <template #body="{ data: row }">{{ row.department ?? '—' }}</template>
        </Column>

        <Column field="event_date" header="Ngày sự kiện" sortable style="width:140px;">
          <template #body="{ data: row }">{{ formatDate(row.event_date) }}</template>
        </Column>

        <Column field="days_until" header="Còn lại" sortable style="width:120px;">
          <template #body="{ data: row }">
            <span :class="['days-badge', daysBadgeClass(row.days_until)]">
              {{ row.days_until === 0 ? 'Hôm nay' : `${row.days_until} ngày` }}
            </span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'

import reminderService, {
  EVENT_TYPE_ICONS,
  EVENT_TYPE_LABELS,
  type EventType,
  type ReminderItem,
  type RemindersResponse,
} from '@/services/reminderService'

const router  = useRouter()
const loading = ref(false)
const data    = ref<RemindersResponse | null>(null)

const daysParam  = ref(30)
const typeFilter = ref<EventType | null>(null)

const daysOptions = [
  { label: '7 ngày tới',  value: 7  },
  { label: '14 ngày tới', value: 14 },
  { label: '30 ngày tới', value: 30 },
  { label: '60 ngày tới', value: 60 },
  { label: '90 ngày tới', value: 90 },
]

const typeOptions = [
  { label: 'Sinh nhật',       value: 'birthday'        },
  { label: 'Thâm niên',      value: 'anniversary'     },
  { label: 'Hết thử việc',   value: 'probation_end'   },
  { label: 'HĐ sắp hết hạn', value: 'contract_expiry' },
]

const allItems = computed<ReminderItem[]>(() => {
  if (!data.value) return []
  return [
    ...data.value.birthday,
    ...data.value.anniversary,
    ...data.value.probation_end,
    ...data.value.contract_expiry,
  ].sort((a, b) => a.days_until - b.days_until)
})

const filteredItems = computed<ReminderItem[]>(() => {
  if (!typeFilter.value) return allItems.value
  return allItems.value.filter(i => i.event_type === typeFilter.value)
})

async function load() {
  loading.value = true
  try {
    const res = await reminderService.getReminders(daysParam.value)
    data.value = res.data
  } finally {
    loading.value = false
  }
}

function goToEmployee(row: ReminderItem) {
  if (row.event_type === 'contract_expiry') {
    router.push(`/employees/${row.employee_id}?tab=contracts`)
  } else {
    router.push(`/employees/${row.employee_id}`)
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function daysBadgeClass(days: number): string {
  if (days === 0) return 'today'
  if (days <= 7)  return 'soon'
  return 'later'
}

onMounted(load)
</script>
