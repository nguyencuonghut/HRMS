<template>
  <div class="ob-detail">
    <!-- Breadcrumb -->
    <nav class="ob-breadcrumb">
      <RouterLink to="/employees">Nhân viên</RouterLink>
      <i class="pi pi-chevron-right" />
      <RouterLink to="/employees/onboarding">Tiếp nhận nhân viên mới</RouterLink>
      <i class="pi pi-chevron-right" />
      <span>{{ checklist?.employee_name ?? '...' }}</span>
    </nav>

    <div v-if="loading" class="ob-loading">
      <ProgressSpinner style="width:40px;height:40px" />
    </div>

    <template v-else-if="checklist">
      <!-- Header card -->
      <div class="ob-card ob-header-card">
        <div class="ob-header-info">
          <div class="ob-header-name">{{ checklist.employee_name }}</div>
          <div class="ob-header-meta">
            <Tag :value="checklist.employee_code" severity="secondary" />
            <span v-if="checklist.department_name" class="ob-meta-sep">·</span>
            <span>{{ checklist.department_name ?? '' }}</span>
            <span class="ob-meta-sep">·</span>
            <span>Vào làm: {{ fmtDate(checklist.start_date) }}</span>
          </div>
          <div class="ob-header-buddy">
            <span class="ob-label">Buddy:</span>
            <Select
              v-model="buddyId"
              :options="users"
              option-label="label"
              option-value="value"
              placeholder="Chưa có buddy"
              show-clear
              style="width: 220px"
              @change="updateBuddy"
            />
          </div>
        </div>
        <div class="ob-header-status">
          <div class="ob-header-pct">{{ checklist.completion_pct.toFixed(0) }}%</div>
          <ProgressBar
            :value="checklist.completion_pct"
            style="height: 10px; width: 200px"
          />
          <Tag
            :value="statusLabel(checklist.status)"
            :severity="statusSeverity(checklist.status)"
            style="margin-top: 0.5rem"
          />
        </div>
      </div>

      <!-- Action bar -->
      <div class="ob-action-bar">
        <Button
          label="Đánh dấu tất cả hoàn thành"
          icon="pi pi-check-circle"
          severity="success"
          outlined
          :disabled="checklist.status !== 'in_progress'"
          @click="markAllDone"
        />
        <Button
          v-if="checklist.status === 'in_progress'"
          label="Hủy checklist"
          icon="pi pi-times"
          severity="danger"
          outlined
          @click="confirmCancel"
        />
      </div>

      <!-- Items table -->
      <div class="ob-card">
        <DataTable
          :value="checklist.items"
          size="small"
          striped-rows
          :row-class="rowClass"
        >
          <template #empty>
            <div class="ob-empty">Không có task nào</div>
          </template>

          <Column header="Task" min-header-width="200px">
            <template #body="{ data }">
              <div>{{ data.task_name }}</div>
            </template>
          </Column>

          <Column header="Nhóm" style="width: 110px">
            <template #body="{ data }">
              <Tag
                :value="groupLabel(data.task_group)"
                :severity="groupSeverity(data.task_group)"
              />
            </template>
          </Column>

          <Column header="Phụ trách" style="width: 180px">
            <template #body="{ data }">
              <Select
                :model-value="data.assignee_user_id"
                :options="users"
                option-label="label"
                option-value="value"
                placeholder="Chưa phân công"
                show-clear
                style="width: 170px"
                :disabled="checklist.status !== 'in_progress'"
                @change="(v) => patchItem(data, { status: data.status, assignee_user_id: (v as any).value })"
              />
            </template>
          </Column>

          <Column header="Hạn" style="width: 110px">
            <template #body="{ data }">
              <span :class="data.is_overdue ? 'ob-overdue' : ''">
                {{ fmtDate(data.due_date) }}
              </span>
            </template>
          </Column>

          <Column header="Trạng thái" style="width: 150px">
            <template #body="{ data }">
              <Select
                :model-value="data.status"
                :options="itemStatusOptions"
                option-label="label"
                option-value="value"
                style="width: 140px"
                :disabled="checklist.status !== 'in_progress'"
                @change="(v) => patchItem(data, { status: (v as any).value })"
              />
            </template>
          </Column>

          <Column header="Ghi chú" style="width: 180px">
            <template #body="{ data }">
              <InputText
                :model-value="data.note ?? ''"
                placeholder="Ghi chú..."
                style="width: 170px"
                :disabled="checklist.status !== 'in_progress'"
                @blur="(e: FocusEvent) => onNoteBlur(data, (e.target as HTMLInputElement).value)"
              />
            </template>
          </Column>

          <Column header="Hoàn thành lúc" style="width: 150px">
            <template #body="{ data }">
              <span v-if="data.completed_at" class="ob-muted">
                {{ fmtDateTime(data.completed_at) }}
              </span>
              <span v-else class="ob-muted">—</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </template>

    <div v-else class="ob-card ob-empty">Không tìm thấy checklist cho nhân viên này.</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import {
  onboardingChecklistService,
  type OnboardingChecklistItemRead,
  type OnboardingChecklistRead,
} from '@/services/onboardingService'
import api from '@/services/api'

const route = useRoute()
const toast = useToast()
const confirm = useConfirm()

const checklist = ref<OnboardingChecklistRead | null>(null)
const loading = ref(false)
const buddyId = ref<number | null>(null)
const users = ref<{ value: number; label: string }[]>([])

const itemStatusOptions = [
  { label: 'Chờ', value: 'pending' },
  { label: 'Đang làm', value: 'in_progress' },
  { label: 'Xong', value: 'done' },
  { label: 'Bỏ qua', value: 'skipped' },
]

onMounted(async () => {
  try {
    const r = await api.get('/users', { params: { page_size: 200 } })
    const list = r.data?.items ?? r.data ?? []
    users.value = list.map((u: { id: number; full_name: string }) => ({ value: u.id, label: u.full_name }))
  } catch { /* ignore */ }
  await loadChecklist()
})

async function loadChecklist() {
  loading.value = true
  const empId = Number(route.params.employee_id)
  try {
    const data = await onboardingChecklistService.getByEmployee(empId)
    checklist.value = data
    buddyId.value = data.buddy_user_id
  } catch {
    checklist.value = null
  } finally {
    loading.value = false
  }
}

async function updateBuddy() {
  if (!checklist.value) return
  try {
    const updated = await onboardingChecklistService.update(checklist.value.id, {
      buddy_user_id: buddyId.value,
    })
    checklist.value = updated
    toast.add({ severity: 'success', summary: 'Đã cập nhật buddy', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể cập nhật buddy', life: 3000 })
  }
}

async function patchItem(
  item: OnboardingChecklistItemRead,
  patch: { status?: string; assignee_user_id?: number | null; note?: string | null },
) {
  if (!checklist.value) return
  try {
    const updated = await onboardingChecklistService.updateItem(checklist.value.id, item.id, {
      status: patch.status ?? item.status,
      assignee_user_id: patch.assignee_user_id !== undefined ? patch.assignee_user_id : item.assignee_user_id,
      note: patch.note !== undefined ? patch.note : item.note,
    })
    // Update item in-place
    const idx = checklist.value.items.findIndex((i) => i.id === item.id)
    if (idx >= 0) checklist.value.items[idx] = updated
    // Reload checklist for completion_pct + status update
    await loadChecklist()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể cập nhật task', life: 3000 })
  }
}

function onNoteBlur(item: OnboardingChecklistItemRead, newNote: string) {
  if (newNote !== (item.note ?? '')) {
    void patchItem(item, { note: newNote || null })
  }
}

async function markAllDone() {
  if (!checklist.value) return
  const pending = checklist.value.items.filter(
    (i) => i.status !== 'done' && i.status !== 'skipped',
  )
  if (pending.length === 0) return
  try {
    await Promise.all(
      pending.map((item) =>
        onboardingChecklistService.updateItem(checklist.value!.id, item.id, {
          status: 'done',
          assignee_user_id: item.assignee_user_id,
          note: item.note,
        }),
      ),
    )
    await loadChecklist()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể cập nhật tất cả task', life: 3000 })
  }
}

function confirmCancel() {
  confirm.require({
    message: 'Bạn có chắc muốn hủy checklist này?',
    header: 'Xác nhận hủy',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Hủy checklist',
    rejectLabel: 'Đóng',
    accept: async () => {
      if (!checklist.value) return
      try {
        const updated = await onboardingChecklistService.update(checklist.value.id, { status: 'cancelled' })
        checklist.value = updated
        toast.add({ severity: 'info', summary: 'Đã hủy checklist', life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể hủy checklist', life: 3000 })
      }
    },
  })
}

function fmtDate(s: string): string {
  return new Date(s).toLocaleDateString('vi-VN')
}

function fmtDateTime(s: string): string {
  return new Date(s).toLocaleString('vi-VN')
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

function groupLabel(g: string): string {
  if (g === 'admin') return 'Hành chính'
  if (g === 'it') return 'IT'
  if (g === 'training') return 'Đào tạo'
  if (g === 'specialty') return 'Chuyên môn'
  return g
}

function groupSeverity(g: string): string {
  if (g === 'admin') return 'secondary'
  if (g === 'it') return 'info'
  if (g === 'training') return 'warn'
  if (g === 'specialty') return 'success'
  return 'secondary'
}

function rowClass(data: OnboardingChecklistItemRead) {
  return data.is_overdue ? 'ob-row-overdue' : ''
}
</script>
