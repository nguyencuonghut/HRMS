<template>
  <div class="ob-task-config">
    <!-- Breadcrumb -->
    <nav class="ob-breadcrumb">
      <RouterLink to="/employees">Nhân viên</RouterLink>
      <i class="pi pi-chevron-right" />
      <RouterLink to="/employees/onboarding">Tiếp nhận nhân viên mới</RouterLink>
      <i class="pi pi-chevron-right" />
      <span>Cấu hình task</span>
    </nav>

    <!-- Toolbar -->
    <div class="ob-toolbar">
      <div class="ob-toolbar-left">
        <span class="ob-page-title">Cấu hình task onboarding</span>
      </div>
      <div class="ob-toolbar-right">
        <Button v-if="canEditEmployees" label="Thêm task mới" icon="pi pi-plus" @click="openAddDialog" />
      </div>
    </div>

    <!-- Table -->
    <div class="ob-card">
      <DataTable
        :value="tasks"
        :loading="loading"
        striped-rows
        size="small"
        edit-mode="row"
        data-key="id"
        v-model:editingRows="editingRows"
        @row-edit-save="onRowSave"
        @row-edit-cancel="editingRows = []"
      >
        <template #empty>
          <div class="ob-empty">Chưa có task nào</div>
        </template>

        <Column field="code" header="Mã" style="width: 160px" />

        <Column field="name" header="Tên task">
          <template #editor="{ data }">
            <InputText v-model="data.name" style="width: 100%" />
          </template>
        </Column>

        <Column field="group" header="Nhóm" style="width: 120px">
          <template #body="{ data }">
            <Tag :value="groupLabel(data.group)" :severity="groupSeverity(data.group)" />
          </template>
          <template #editor="{ data }">
            <Select
              v-model="data.group"
              :options="groupOptions"
              option-label="label"
              option-value="value"
              style="width: 120px"
            />
          </template>
        </Column>

        <Column field="due_offset_days" header="Hạn (ngày)" style="width: 110px">
          <template #editor="{ data }">
            <InputNumber v-model="data.due_offset_days" :min="0" style="width: 100px" />
          </template>
        </Column>

        <Column field="sort_order" header="Thứ tự" style="width: 90px">
          <template #editor="{ data }">
            <InputNumber v-model="data.sort_order" :min="0" style="width: 80px" />
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 100px">
          <template #body="{ data }">
            <ToggleSwitch
              v-if="canEditEmployees"
              :model-value="data.is_active"
              @change="toggleActive(data)"
            />
            <span v-else>{{ data.is_active ? 'Bật' : 'Tắt' }}</span>
          </template>
        </Column>

        <Column v-if="canEditEmployees" row-editor style="width: 100px" />

        <Column v-if="canEditEmployees" header="Xóa" style="width: 70px">
          <template #body="{ data }">
            <Button
              icon="pi pi-trash"
              text
              severity="danger"
              size="small"
              @click="confirmDelete(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Add dialog -->
    <Dialog
      v-model:visible="showAddDialog"
      header="Thêm task mới"
      :modal="true"
      :style="{ width: '440px' }"
    >
      <div class="ob-form">
        <div class="ob-form-field">
          <label class="ob-form-label">Mã <span class="ob-required">*</span></label>
          <InputText v-model="addForm.code" placeholder="VD: IT_VPN_SETUP" style="width: 100%" />
        </div>
        <div class="ob-form-field">
          <label class="ob-form-label">Tên task <span class="ob-required">*</span></label>
          <InputText v-model="addForm.name" style="width: 100%" />
        </div>
        <div class="ob-form-field">
          <label class="ob-form-label">Nhóm</label>
          <Select
            v-model="addForm.group"
            :options="groupOptions"
            option-label="label"
            option-value="value"
            style="width: 100%"
          />
        </div>
        <div class="ob-form-field">
          <label class="ob-form-label">Hạn (ngày kể từ ngày vào)</label>
          <InputNumber v-model="addForm.due_offset_days" :min="0" style="width: 100%" />
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined @click="showAddDialog = false" />
        <Button v-if="canEditEmployees" label="Thêm" icon="pi pi-plus" :loading="saving" @click="addTask" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import {
  onboardingTaskService,
  type OnboardingTaskRead,
} from '@/services/onboardingService'
import { usePermissionGate } from '@/composables/usePermissionGate'

const toast = useToast()
const confirm = useConfirm()
const permissionGate = usePermissionGate()
const canEditEmployees = computed(() => permissionGate.canEdit('employees'))

const tasks = ref<OnboardingTaskRead[]>([])
const loading = ref(false)
const saving = ref(false)
const showAddDialog = ref(false)
const editingRows = ref<OnboardingTaskRead[]>([])

const addForm = reactive({
  code: '',
  name: '',
  group: 'admin' as string,
  due_offset_days: 3,
})

const groupOptions = [
  { label: 'Hành chính', value: 'admin' },
  { label: 'IT', value: 'it' },
  { label: 'Đào tạo', value: 'training' },
  { label: 'Chuyên môn', value: 'specialty' },
]

onMounted(loadTasks)

async function loadTasks() {
  loading.value = true
  try {
    tasks.value = await onboardingTaskService.list({ is_active: true })
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể tải danh sách task', life: 3000 })
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  addForm.code = ''
  addForm.name = ''
  addForm.group = 'admin'
  addForm.due_offset_days = 3
  showAddDialog.value = true
}

async function addTask() {
  if (!addForm.code || !addForm.name) {
    toast.add({ severity: 'warn', summary: 'Thiếu thông tin', detail: 'Vui lòng điền mã và tên task', life: 3000 })
    return
  }
  saving.value = true
  try {
    await onboardingTaskService.create({ ...addForm })
    toast.add({ severity: 'success', summary: 'Đã thêm task', life: 2000 })
    showAddDialog.value = false
    await loadTasks()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không thể thêm task'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    saving.value = false
  }
}

async function onRowSave(event: { newData: OnboardingTaskRead }) {
  const d = event.newData
  try {
    await onboardingTaskService.update(d.id, {
      name: d.name,
      group: d.group,
      due_offset_days: d.due_offset_days,
      sort_order: d.sort_order,
    })
    toast.add({ severity: 'success', summary: 'Đã lưu', life: 2000 })
    await loadTasks()
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể lưu', life: 3000 })
  }
}

async function toggleActive(task: OnboardingTaskRead) {
  try {
    await onboardingTaskService.update(task.id, { is_active: !task.is_active })
    task.is_active = !task.is_active
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể cập nhật', life: 3000 })
  }
}

function confirmDelete(task: OnboardingTaskRead) {
  confirm.require({
    message: `Xóa task "${task.name}"?`,
    header: 'Xác nhận xóa',
    icon: 'pi pi-trash',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    accept: async () => {
      try {
        await onboardingTaskService.delete(task.id)
        toast.add({ severity: 'success', summary: 'Đã xóa task', life: 2000 })
        await loadTasks()
      } catch {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể xóa task', life: 3000 })
      }
    },
  })
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
</script>
