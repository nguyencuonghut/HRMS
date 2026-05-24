<template>
  <div class="kpi-history-tab">
    <!-- ── Phần 1: KPI Tháng ──────────────────────────────────────────────── -->
    <div class="kpi-section-title">KPI Tháng</div>

    <div class="kpi-ht-toolbar">
      <Select
        v-model="selectedYear"
        :options="yearOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả năm"
        :show-clear="true"
        filter
        class="kpi-ht-year-select"
        @change="loadKpiHistory"
      />
      <Button icon="pi pi-refresh" severity="secondary" text v-tooltip="'Tải lại'" @click="loadKpiHistory" />
    </div>

    <DataTable
      :value="kpiRows"
      :loading="loadingKpi"
      size="small"
      striped-rows
      class="kpi-ht-table"
    >
      <template #empty>
        <div class="perf-empty">Không có dữ liệu KPI tháng</div>
      </template>
      <Column field="year" header="Năm" style="width:80px" />
      <Column field="month" header="Tháng" style="width:80px">
        <template #body="{ data }">Tháng {{ data.month }}</template>
      </Column>
      <Column field="score" header="Điểm KPI" style="width:110px">
        <template #body="{ data }">
          <span :class="scoreClass(parseFloat(data.score))">{{ data.score }}</span>
        </template>
      </Column>
      <Column field="note" header="Ghi chú">
        <template #body="{ data }">
          <span class="perf-muted">{{ data.note || '—' }}</span>
        </template>
      </Column>
      <Column field="created_by_name" header="Người nhập">
        <template #body="{ data }">
          <span class="perf-muted">{{ data.created_by_name || '—' }}</span>
        </template>
      </Column>
    </DataTable>

    <!-- ── Phần 2: Đánh giá Cuối năm ─────────────────────────────────────── -->
    <div class="kpi-section-title" style="margin-top:1.5rem">Đánh giá Cuối năm</div>

    <DataTable
      :value="reviewRows"
      :loading="loadingReviews"
      size="small"
      striped-rows
      class="kpi-ht-table"
    >
      <template #empty>
        <div class="perf-empty">Không có đánh giá cuối năm</div>
      </template>
      <Column field="year" header="Năm" style="width:80px" />
      <Column field="avg_score" header="Điểm TB" style="width:100px">
        <template #body="{ data }">
          <span v-if="data.avg_score" :class="scoreClass(parseFloat(data.avg_score))">
            {{ parseFloat(data.avg_score).toFixed(1) }}
          </span>
          <span v-else class="perf-muted">—</span>
        </template>
      </Column>
      <Column field="months_count" header="Số tháng" style="width:90px">
        <template #body="{ data }">{{ data.months_count }}/12</template>
      </Column>
      <Column field="rating_label" header="Xếp loại" style="width:140px">
        <template #body="{ data }">
          <Tag :value="data.rating_label" :severity="ratingSeverity(data.rating)" />
        </template>
      </Column>
      <Column field="review_note" header="Nhận xét">
        <template #body="{ data }">
          <span class="perf-muted">{{ data.review_note || '—' }}</span>
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import performanceService, { type KpiMonthlyRead, type YearlyReviewRead } from '@/services/performanceService'

const props = defineProps<{ employeeId: number }>()

const selectedYear = ref<number | null>(null)
const kpiRows = ref<KpiMonthlyRead[]>([])
const reviewRows = ref<YearlyReviewRead[]>([])
const loadingKpi = ref(false)
const loadingReviews = ref(false)

const currentYear = new Date().getFullYear()
const yearOptions = computed(() => {
  const years = []
  for (let y = currentYear + 1; y >= 2010; y--) {
    years.push({ label: `${y}`, value: y })
  }
  return years
})

async function loadKpiHistory() {
  loadingKpi.value = true
  try {
    const res = await performanceService.getEmployeeKpiHistory(props.employeeId, selectedYear.value)
    kpiRows.value = res.data
  } finally {
    loadingKpi.value = false
  }
}

async function loadReviewHistory() {
  loadingReviews.value = true
  try {
    const res = await performanceService.getEmployeeReviewHistory(props.employeeId)
    reviewRows.value = res.data
  } finally {
    loadingReviews.value = false
  }
}

function scoreClass(score: number) {
  if (score >= 95) return 'perf-score perf-score-high'
  if (score > 85) return 'perf-score perf-score-mid'
  return 'perf-score perf-score-low'
}

function ratingSeverity(rating: string) {
  if (rating === 'xuat_sac') return 'success'
  if (rating === 'tot') return 'info'
  if (rating === 'dat') return 'warn'
  return 'danger'
}

onMounted(() => {
  loadKpiHistory()
  loadReviewHistory()
})
</script>
