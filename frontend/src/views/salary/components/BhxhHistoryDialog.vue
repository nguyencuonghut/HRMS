<template>
  <Dialog
    v-model:visible="visible"
    :header="`Lịch sử mức lương BHXH — ${employee?.employee_code} ${employee?.full_name}`"
    modal
    :style="{ width: '720px' }"
    @hide="emit('hide')"
  >
    <!-- Summary row -->
    <div v-if="employee" class="salary-history-summary">
      <span class="salary-history-summary-item">
        <i class="pi pi-money-bill" />
        <strong>Mức hiện tại:</strong>
        {{ employee.insurance_basis_amount ? fmtMoney(employee.insurance_basis_amount) : '—' }}
      </span>
      <span class="salary-history-summary-item">
        <i class="pi pi-tag" />
        <strong>Nguồn:</strong> {{ sourceLabel(employee.insurance_basis_source) }}
      </span>
      <span class="salary-history-summary-item">
        <i class="pi pi-circle-fill" :class="statusIconClass(employee.participation_status)" />
        <strong>TT bảo hiểm:</strong> {{ statusLabel(employee.participation_status) }}
      </span>
      <span v-if="employee.has_discrepancy" class="salary-basis-warn">
        <i class="pi pi-exclamation-triangle" />
        Mức thủ công khác hợp đồng đang hiệu lực
      </span>
    </div>

    <!-- History table -->
    <DataTable
      :value="items"
      :loading="loading"
      size="small"
      :row-class="historyRowClass"
    >
      <template #empty>
        <div style="padding: 1rem; color: var(--p-text-muted-color)">Chưa có lịch sử mức lương BHXH</div>
      </template>

      <Column header="Ngày hiệu lực" style="min-width: 130px">
        <template #body="{ data }: { data: BhxhSalaryHistoryItem }">
          {{ fmtDate(data.effective_date) }}
        </template>
      </Column>

      <Column header="Mức lương BHXH" style="min-width: 150px">
        <template #body="{ data }: { data: BhxhSalaryHistoryItem }">
          <span class="salary-basis-amount">{{ fmtMoney(data.basis_amount) }}</span>
          <span v-if="data.old_basis_amount" style="margin-left: 0.5rem; font-size: 0.8rem; color: var(--p-text-muted-color)">
            (trước: {{ fmtMoney(data.old_basis_amount) }})
          </span>
        </template>
      </Column>

      <Column header="Loại thay đổi" style="min-width: 140px">
        <template #body="{ data }: { data: BhxhSalaryHistoryItem }">
          <span v-if="data.source_type === 'contract'" class="salary-history-source-contract">
            <i class="pi pi-file-edit" /> Hợp đồng
          </span>
          <span v-else class="salary-history-source-adjustment">
            <i class="pi pi-pencil" /> Điều chỉnh
          </span>
        </template>
      </Column>

      <Column header="Ghi chú" style="min-width: 160px">
        <template #body="{ data }: { data: BhxhSalaryHistoryItem }">
          {{ data.note || '—' }}
        </template>
      </Column>

      <Column header="Số QĐ" style="min-width: 100px">
        <template #body="{ data }: { data: BhxhSalaryHistoryItem }">
          {{ data.decision_number || '—' }}
        </template>
      </Column>

      <Column header="Người điều chỉnh" style="min-width: 140px">
        <template #body="{ data }: { data: BhxhSalaryHistoryItem }">
          {{ data.created_by_name || '—' }}
        </template>
      </Column>
    </DataTable>

    <template #footer>
      <Button label="Đóng" text @click="visible = false" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'

import salaryService, { type BhxhSalaryHistoryItem, type SalaryEmployeeRow } from '@/services/salaryService'

const props = defineProps<{
  modelValue: boolean
  employee: SalaryEmployeeRow | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'hide'): void
}>()

const visible = ref(props.modelValue)
const items = ref<BhxhSalaryHistoryItem[]>([])
const loading = ref(false)

function historyRowClass(data: BhxhSalaryHistoryItem) {
  const first = items.value[0]
  if (!first) return ''
  return data.effective_date === first.effective_date &&
    data.basis_amount === first.basis_amount &&
    data.source_type === first.source_type
    ? 'salary-history-current-row'
    : ''
}

watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

watch(() => props.employee, async (emp) => {
  if (!emp) return
  loading.value = true
  try {
    const res = await salaryService.getEmployeeBhxhHistory(emp.employee_id)
    items.value = res.data
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}, { immediate: true })

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function fmtMoney(val: string | null) {
  if (!val) return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

function sourceLabel(src: string | null) {
  if (src === 'contract') return 'Hợp đồng'
  if (src === 'manual_fixed') return 'Thủ công'
  if (src === 'computed') return 'Tính tự động'
  return '—'
}

function statusLabel(s: string | null) {
  if (s === 'active') return 'Đang đóng'
  if (s === 'paused') return 'Tạm dừng'
  if (s === 'stopped') return 'Đã dừng'
  return '—'
}

function statusIconClass(s: string | null) {
  if (s === 'active') return 'salary-status-active'
  if (s === 'paused') return 'salary-status-paused'
  return 'salary-status-stopped'
}
</script>
