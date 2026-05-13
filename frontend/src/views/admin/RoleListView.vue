<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Vai trò & Quyền</h2>
        <span class="subtitle">Quản lý vai trò và phân quyền hệ thống</span>
      </div>
      <Button label="Thêm vai trò" icon="pi pi-plus" @click="openCreate" />
    </div>

    <!-- DataTable -->
    <div class="card">
      <DataTable
        :value="roles"
        :loading="loading"
        responsive-layout="scroll"
        sort-field="id"
        :sort-order="1"
      >
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-shield" />
            <span>Không có dữ liệu</span>
          </div>
        </template>

        <Column field="code" header="Mã vai trò" sortable style="width: 160px">
          <template #body="{ data }">
            <code class="role-code">{{ data.code }}</code>
          </template>
        </Column>

        <Column field="name" header="Tên vai trò" sortable style="min-width: 180px" />

        <Column field="description" header="Mô tả" style="min-width: 200px">
          <template #body="{ data }">
            <span class="muted-text">{{ data.description ?? '—' }}</span>
          </template>
        </Column>

        <Column field="permission_count" header="Số quyền" sortable style="width: 110px">
          <template #body="{ data }">
            <Badge :value="data.permission_count" severity="secondary" />
          </template>
        </Column>

        <Column field="is_system" header="Loại" sortable style="width: 110px">
          <template #body="{ data }">
            <Tag
              :value="data.is_system ? 'Hệ thống' : 'Tuỳ chỉnh'"
              :severity="data.is_system ? 'warn' : 'info'"
            />
          </template>
        </Column>

        <Column header="" style="width: 130px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button
                icon="pi pi-table"
                severity="info"
                text rounded size="small"
                v-tooltip.top="'Ma trận quyền'"
                @click="openMatrix(data)"
              />
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text rounded size="small"
                v-tooltip.top="'Chỉnh sửa'"
                :disabled="data.is_system"
                @click="openEdit(data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                text rounded size="small"
                v-tooltip.top="data.is_system ? 'Không thể xóa vai trò hệ thống' : 'Xóa'"
                :disabled="data.is_system"
                @click="confirmDelete(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Form dialog (create / edit) -->
    <RoleFormDialog
      v-model="formVisible"
      :role="editingRole"
      @saved="loadData"
    />

    <!-- Permission matrix dialog -->
    <PermissionMatrixDialog
      v-model="matrixVisible"
      :role="matrixRole"
      @saved="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'

import RoleFormDialog from './RoleFormDialog.vue'
import PermissionMatrixDialog from './PermissionMatrixDialog.vue'
import roleService, { type RoleListItem } from '@/services/roleService'

const toast   = useToast()
const confirm = useConfirm()

const loading      = ref(false)
const roles        = ref<RoleListItem[]>([])
const formVisible  = ref(false)
const editingRole  = ref<RoleListItem | null>(null)
const matrixVisible = ref(false)
const matrixRole    = ref<RoleListItem | null>(null)

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const d = err.response?.data?.detail
  if (Array.isArray(d)) return d.map((x: { msg: string }) => x.msg).join('; ')
  return typeof d === 'string' ? d : 'Đã xảy ra lỗi, vui lòng thử lại'
}

async function loadData() {
  loading.value = true
  try {
    const resp = await roleService.list()
    roles.value = resp.data
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingRole.value = null
  formVisible.value = true
}

function openEdit(role: RoleListItem) {
  editingRole.value = role
  formVisible.value = true
}

function openMatrix(role: RoleListItem) {
  matrixRole.value   = role
  matrixVisible.value = true
}

function confirmDelete(role: RoleListItem) {
  confirm.require({
    message:     `Xóa vai trò "${role.name}"? Thao tác này không thể hoàn tác.`,
    header:      'Xác nhận xóa',
    icon:        'pi pi-exclamation-triangle',
    acceptLabel: 'Xóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await roleService.delete(role.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã xóa vai trò', life: 3000 })
        await loadData()
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
      }
    },
  })
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 1.25rem;
  h2 { margin: 0 0 0.2rem; font-size: 1.5rem; font-weight: 700; }
  .subtitle { color: var(--p-text-muted-color); font-size: 0.875rem; }
}

.card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px; overflow: hidden;
}

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.5rem; padding: 3rem; color: var(--p-text-muted-color);
  i { font-size: 2rem; opacity: 0.3; }
}

.role-code {
  font-family: monospace; font-size: 0.85rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 30%, transparent);
  padding: 0.15rem 0.45rem; border-radius: 4px;
  white-space: nowrap;
}

.muted-text  { color: var(--p-text-muted-color); font-size: 0.875rem; }
.action-cell { display: flex; gap: 0.1rem; justify-content: flex-end; }
</style>
