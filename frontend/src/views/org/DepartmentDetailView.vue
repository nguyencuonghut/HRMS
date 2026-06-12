<template>
  <div class="dept-detail-view">
    <Toast />

    <div class="page-header">
      <div>
        <h2>{{ detail?.department.name ?? 'Chi tiết phòng / ban' }}</h2>
        <span class="subtitle">
          <template v-if="detail">
            {{ detail.department.code }} · {{ detail.department.dept_type_label }}
            <template v-if="detail.parent">
              · Thuộc {{ detail.parent.name }}
            </template>
          </template>
          <template v-else>
            Đang tải thông tin đơn vị
          </template>
        </span>
      </div>
      <div class="page-header-actions">
        <Button
          label="Làm mới"
          icon="pi pi-refresh"
          severity="secondary"
          outlined
          :loading="loading"
          @click="loadDetail"
        />
        <Button
          label="Quay lại"
          icon="pi pi-arrow-left"
          severity="secondary"
          text
          @click="goBack"
        />
      </div>
    </div>

    <div v-if="detail" class="dept-meta-strip">
      <Tag
        :value="detail.department.is_active ? 'Hoạt động' : 'Đã khóa'"
        :severity="detail.department.is_active ? 'success' : 'danger'"
      />
      <span v-if="detail.parent" class="dept-meta-item">
        Đơn vị cha:
        <button type="button" class="dept-inline-link" @click="goToDepartment(detail.parent.id)">
          {{ detail.parent.name }}
        </button>
      </span>
      <span class="dept-meta-item">Mã: {{ detail.department.code }}</span>
    </div>

    <div class="dept-summary-grid">
      <article v-for="card in summaryCards" :key="card.label" class="dept-summary-card card">
        <span class="dept-summary-label">{{ card.label }}</span>
        <strong class="dept-summary-value">{{ card.value }}</strong>
        <small v-if="card.note" class="dept-summary-note">{{ card.note }}</small>
      </article>
    </div>

    <div class="card dept-employees-card">
      <div class="dept-section-head">
        <div>
          <h3>Nhân sự trực tiếp</h3>
          <p>Danh sách nhân sự hiện đang thuộc đúng đơn vị này.</p>
        </div>
      </div>

      <DataTable
        :value="detail?.direct_employees ?? []"
        :loading="loading"
        responsive-layout="scroll"
      >
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-users" />
            <span>Đơn vị này chưa có nhân sự trực tiếp.</span>
          </div>
        </template>

        <Column field="display_code" header="Mã NV" style="width: 120px" />

        <Column field="full_name" header="Họ và tên" style="min-width: 220px">
          <template #body="{ data }">
            <button type="button" class="dept-inline-link" @click="goToEmployee(data.id)">
              {{ data.full_name }}
            </button>
          </template>
        </Column>

        <Column field="job_position_name" header="Vị trí" style="min-width: 220px">
          <template #body="{ data }">
            {{ data.job_position_name || data.job_title_name || '—' }}
          </template>
        </Column>

        <Column field="status" header="Trạng thái" style="width: 140px">
          <template #body="{ data }">
            <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
          </template>
        </Column>

        <Column field="start_date" header="Ngày vào làm" style="width: 140px">
          <template #body="{ data }">
            {{ formatDate(data.start_date) }}
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import departmentService, { type DepartmentDetailRead } from '@/services/departmentService'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const loading = ref(false)
const detail = ref<DepartmentDetailRead | null>(null)

const departmentId = computed(() => Number(route.params.id))

const summaryCards = computed(() => {
  if (!detail.value) {
    return [
      { label: 'Nhân sự trực tiếp', value: '—', note: null },
      { label: 'Nhân sự toàn cây', value: '—', note: null },
      { label: 'Đơn vị con trực tiếp', value: '—', note: null },
      { label: 'Vị trí công việc', value: '—', note: null },
    ]
  }
  return [
    {
      label: 'Nhân sự trực tiếp',
      value: String(detail.value.summary.direct_headcount),
      note: 'Đang thuộc đúng đơn vị hiện tại',
    },
    {
      label: 'Nhân sự toàn cây',
      value: String(detail.value.summary.total_headcount),
      note: 'Bao gồm tất cả đơn vị con',
    },
    {
      label: 'Đơn vị con trực tiếp',
      value: String(detail.value.summary.direct_child_count),
      note: null,
    },
    {
      label: 'Vị trí công việc',
      value: String(detail.value.summary.job_position_count),
      note: 'Thuộc riêng đơn vị hiện tại',
    },
  ]
})

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

function formatDate(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('vi-VN')
}

function statusLabel(status: string) {
  switch (status) {
    case 'official':
      return 'Chính thức'
    case 'probation':
      return 'Thử việc'
    case 'long_leave':
      return 'Nghỉ dài hạn'
    case 'resigned':
      return 'Đã nghỉ việc'
    default:
      return status
  }
}

function statusSeverity(status: string) {
  switch (status) {
    case 'official':
      return 'success'
    case 'probation':
      return 'warn'
    case 'long_leave':
      return 'info'
    case 'resigned':
      return 'danger'
    default:
      return 'secondary'
  }
}

async function loadDetail() {
  if (!Number.isFinite(departmentId.value)) {
    toast.add({ severity: 'error', summary: 'Không hợp lệ', detail: 'ID phòng / ban không hợp lệ', life: 4000 })
    return
  }

  loading.value = true
  try {
    const response = await departmentService.getDetail(departmentId.value)
    detail.value = response.data
  } catch (e) {
    detail.value = null
    toast.add({
      severity: 'error',
      summary: 'Không tải được chi tiết phòng / ban',
      detail: apiError(e),
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

function goToDepartment(id: number) {
  router.push({ name: 'org-department-detail', params: { id } })
}

function goToEmployee(id: number) {
  router.push({ name: 'employee-detail', params: { id } })
}

function goBack() {
  router.push({ name: 'org-departments' })
}

watch(() => route.params.id, loadDetail)

onMounted(loadDetail)
</script>

<style scoped>
.dept-detail-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dept-meta-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.dept-meta-item {
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
}

.dept-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.dept-summary-card {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.dept-summary-label {
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

.dept-summary-value {
  font-size: 1.8rem;
  line-height: 1;
}

.dept-summary-note {
  color: var(--p-text-muted-color);
}

.dept-section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.dept-section-head h3 {
  margin: 0;
}

.dept-section-head p {
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
}

.dept-inline-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--p-primary-color);
  cursor: pointer;
  font: inherit;
}

.dept-inline-link:hover,
.dept-inline-link:focus-visible {
  text-decoration: underline;
}

@media (max-width: 960px) {
  .dept-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .dept-summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
