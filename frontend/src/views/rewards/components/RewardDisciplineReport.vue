<template>
  <Toast />

  <!-- Toolbar -->
  <div class="report-toolbar">
    <div class="rewards-field">
      <label class="rewards-label">Từ ngày</label>
      <DatePicker v-model="fromDate" dateFormat="dd/mm/yy" showIcon />
    </div>
    <div class="rewards-field">
      <label class="rewards-label">Đến ngày</label>
      <DatePicker v-model="toDate" dateFormat="dd/mm/yy" showIcon />
    </div>
    <div class="rewards-field">
      <label class="rewards-label">Phòng ban</label>
      <Select
        v-model="filterDeptId"
        :options="deptOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Tất cả phòng ban"
        filter
        style="width: 220px"
      />
    </div>
    <Button
      label="Xem báo cáo"
      icon="pi pi-chart-bar"
      :loading="loading"
      @click="load()"
    />
    <Button
      label="Xuất Excel"
      icon="pi pi-download"
      severity="secondary"
      :loading="exportLoading"
      :disabled="!report"
      @click="exportExcel"
    />
  </div>

  <!-- Content (visible after first load) -->
  <template v-if="report">
    <!-- Summary Cards -->
    <div class="report-summary-cards">
      <div class="report-card report-card-reward">
        <i class="pi pi-star-fill report-card-icon" />
        <div class="report-card-label">Khen thưởng</div>
        <div class="report-card-value">{{ report.summary.total_rewards }}</div>
        <div class="report-card-sub">{{ fmtVND(report.summary.total_reward_value) }}</div>
      </div>
      <div class="report-card report-card-disc">
        <i class="pi pi-ban report-card-icon" />
        <div class="report-card-label">Kỷ luật</div>
        <div class="report-card-value">{{ report.summary.total_disciplines }}</div>
        <div class="report-card-sub">quyết định</div>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="report-stats-grid">
      <!-- By reward type -->
      <div class="report-stat-section">
        <div class="report-stat-title">Theo loại khen thưởng</div>
        <DataTable :value="report.summary.by_reward_type" size="small">
          <Column field="reward_type_name" header="Loại khen thưởng" />
          <Column field="count" header="Số lượng" style="width: 100px; text-align: center" />
          <Column header="Tổng giá trị" style="width: 150px; text-align: right">
            <template #body="{ data }">
              {{ fmtVND(data.total_value) }}
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- By discipline form -->
      <div class="report-stat-section">
        <div class="report-stat-title">Theo hình thức kỷ luật</div>
        <DataTable :value="report.summary.by_discipline_form" size="small">
          <Column header="Hình thức">
            <template #body="{ data }">
              <Tag
                :value="data.discipline_form_label"
                :severity="discSeverity(data.discipline_form)"
                :class="data.discipline_form === 'cach_chuc' ? 'disc-tag-cach-chuc' : ''"
              />
            </template>
          </Column>
          <Column field="count" header="Số lượng" style="width: 100px; text-align: center" />
        </DataTable>
      </div>
    </div>

    <!-- By department (full width) -->
    <div class="report-stat-full">
      <div class="report-stat-section">
        <div class="report-stat-title">Theo phòng ban</div>
        <DataTable :value="report.summary.by_department" size="small">
          <Column header="Phòng ban">
            <template #body="{ data }">
              <span v-if="data.department_name" class="rewards-emp-name">{{ data.department_name }}</span>
              <span v-else class="report-dept-null">Chưa phân phòng ban</span>
            </template>
          </Column>
          <Column header="Số khen thưởng" style="width: 160px; text-align: center">
            <template #body="{ data }">
              <span class="report-count-reward">{{ data.reward_count }}</span>
            </template>
          </Column>
          <Column header="Số kỷ luật" style="width: 140px; text-align: center">
            <template #body="{ data }">
              <span class="report-count-disc">{{ data.discipline_count }}</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- Detail tabs -->
    <div class="report-detail">
      <Tabs v-model:value="activeDetailTab">
        <TabList>
          <Tab value="rewards">Khen thưởng ({{ report.total_rewards }})</Tab>
          <Tab value="disciplines">Kỷ luật ({{ report.total_disciplines }})</Tab>
        </TabList>

        <TabPanels>
          <!-- Reward items -->
          <TabPanel value="rewards">
            <DataTable :value="report.reward_items" size="small" :loading="loading">
              <template #empty>
                <span class="rewards-empty">Không có dữ liệu khen thưởng</span>
              </template>
              <Column header="Nhân viên" style="min-width: 200px">
                <template #body="{ data }">
                  <div>
                    <span class="rewards-emp-code">{{ data.employee_code }}</span>
                    <span class="rewards-emp-sep">·</span>
                    <span class="rewards-emp-name">{{ data.employee_name }}</span>
                  </div>
                  <div v-if="data.department_name" class="rewards-emp-dept">{{ data.department_name }}</div>
                </template>
              </Column>
              <Column field="reward_type_name" header="Loại khen thưởng" style="min-width: 140px" />
              <Column field="title" header="Tiêu đề" style="min-width: 160px" />
              <Column header="Ngày KT" style="width: 110px">
                <template #body="{ data }">{{ fmtDate(data.reward_date) }}</template>
              </Column>
              <Column header="Giá trị" style="width: 130px">
                <template #body="{ data }">
                  <span v-if="data.value" class="rewards-value">{{ fmtVND(data.value) }}</span>
                  <span v-else class="rewards-muted">—</span>
                </template>
              </Column>
              <Column header="Số QĐ" style="width: 120px">
                <template #body="{ data }">
                  <span v-if="data.decision_number">{{ data.decision_number }}</span>
                  <span v-else class="rewards-muted">—</span>
                </template>
              </Column>
            </DataTable>

            <Paginator
              v-if="report.total_rewards > pageSize"
              :rows="pageSize"
              :totalRecords="report.total_rewards"
              :first="(rewardPage - 1) * pageSize"
              @page="onRewardPage"
            />
          </TabPanel>

          <!-- Discipline items -->
          <TabPanel value="disciplines">
            <DataTable :value="report.discipline_items" size="small" :loading="loading">
              <template #empty>
                <span class="rewards-empty">Không có dữ liệu kỷ luật</span>
              </template>
              <Column header="Nhân viên" style="min-width: 200px">
                <template #body="{ data }">
                  <div>
                    <span class="rewards-emp-code">{{ data.employee_code }}</span>
                    <span class="rewards-emp-sep">·</span>
                    <span class="rewards-emp-name">{{ data.employee_name }}</span>
                  </div>
                  <div v-if="data.department_name" class="rewards-emp-dept">{{ data.department_name }}</div>
                </template>
              </Column>
              <Column header="Hình thức" style="min-width: 140px">
                <template #body="{ data }">
                  <Tag
                    :value="data.discipline_form_label"
                    :severity="discSeverity(data.discipline_form)"
                    :class="data.discipline_form === 'cach_chuc' ? 'disc-tag-cach-chuc' : ''"
                  />
                </template>
              </Column>
              <Column header="Tiêu đề / QĐ" style="min-width: 160px">
                <template #body="{ data }">
                  <div>{{ data.title }}</div>
                  <div v-if="data.decision_number" class="rewards-decision-num">{{ data.decision_number }}</div>
                </template>
              </Column>
              <Column header="Ngày vi phạm" style="width: 120px">
                <template #body="{ data }">{{ fmtDate(data.violation_date) }}</template>
              </Column>
              <Column header="Ngày hiệu lực" style="width: 120px">
                <template #body="{ data }">{{ fmtDate(data.effective_date) }}</template>
              </Column>
            </DataTable>

            <Paginator
              v-if="report.total_disciplines > pageSize"
              :rows="pageSize"
              :totalRecords="report.total_disciplines"
              :first="(disciplinePage - 1) * pageSize"
              @page="onDisciplinePage"
            />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  </template>

  <!-- Empty state before first load -->
  <div v-else-if="!loading" class="rewards-placeholder">
    <i class="pi pi-chart-bar" />
    <span>Chọn khoảng thời gian và nhấn "Xem báo cáo"</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import rewardReportService from '@/services/rewardReportService'
import type { RewardDisciplineReportPage } from '@/services/rewardReportService'
import departmentService from '@/services/departmentService'
import type { DepartmentRead } from '@/services/departmentService'
import { toLocalIso } from '@/utils/format'

// ── Toast ─────────────────────────────────────────────────────────────────────
const toast = useToast()

// ── State ─────────────────────────────────────────────────────────────────────
const loading = ref(false)
const exportLoading = ref(false)
const fromDate = ref<Date>(new Date(new Date().getFullYear(), 0, 1))   // Jan 1 this year
const toDate = ref<Date>(new Date(new Date().getFullYear(), 11, 31))   // Dec 31 this year
const filterDeptId = ref<number | null>(null)
const departments = ref<DepartmentRead[]>([])
const report = ref<RewardDisciplineReportPage | null>(null)
const rewardPage = ref(1)
const disciplinePage = ref(1)
const pageSize = 20
const activeDetailTab = ref('rewards')

// ── Dept options for Select ───────────────────────────────────────────────────
const deptOptions = computed(() => [
  { label: 'Tất cả phòng ban', value: null },
  ...departments.value.map((d) => ({ label: d.name, value: d.id })),
])

// ── Helpers ───────────────────────────────────────────────────────────────────
function toApiDate(d: Date): string {
  return toLocalIso(d)
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

function fmtVND(val: string | number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return Number(val).toLocaleString('vi-VN') + ' đ'
}

function discSeverity(form: string): 'success' | 'warn' | 'danger' {
  if (form === 'khien_trach') return 'success'
  if (form === 'keo_dai_nang_luong') return 'warn'
  return 'danger'
}

// ── Load report ───────────────────────────────────────────────────────────────
async function load(opts?: { rewardPage?: number; disciplinePage?: number }) {
  if (!fromDate.value || !toDate.value) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng chọn khoảng thời gian', life: 3000 })
    return
  }
  loading.value = true
  try {
    const res = await rewardReportService.getSummary({
      from_date: toApiDate(fromDate.value),
      to_date: toApiDate(toDate.value),
      department_id: filterDeptId.value,
      reward_page: opts?.rewardPage ?? rewardPage.value,
      reward_page_size: pageSize,
      discipline_page: opts?.disciplinePage ?? disciplinePage.value,
      discipline_page_size: pageSize,
    })
    report.value = res.data
    if (opts?.rewardPage) rewardPage.value = opts.rewardPage
    if (opts?.disciplinePage) disciplinePage.value = opts.disciplinePage
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải báo cáo', life: 3000 })
  } finally {
    loading.value = false
  }
}

// ── Pagination handlers ───────────────────────────────────────────────────────
function onRewardPage(event: { page: number }) {
  load({ rewardPage: event.page + 1, disciplinePage: disciplinePage.value })
}

function onDisciplinePage(event: { page: number }) {
  load({ rewardPage: rewardPage.value, disciplinePage: event.page + 1 })
}

// ── Export Excel ──────────────────────────────────────────────────────────────
async function exportExcel() {
  exportLoading.value = true
  try {
    const res = await rewardReportService.exportExcel({
      from_date: toApiDate(fromDate.value),
      to_date: toApiDate(toDate.value),
      department_id: filterDeptId.value,
    })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `khen_thuong_ky_luat_${toApiDate(fromDate.value)}_${toApiDate(toDate.value)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xuất Excel', life: 3000 })
  } finally {
    exportLoading.value = false
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch {
    // non-critical, ignore
  }
})
</script>
