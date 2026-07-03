<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Tài khoản người dùng</h2>
        <span class="subtitle">Quản lý tài khoản và phân quyền hệ thống</span>
      </div>
      <Button label="Thêm mới" icon="pi pi-plus" @click="openCreate" />
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <Select
        v-model="filterActive"
        :options="activeOptions"
        option-label="label"
        option-value="value"
        placeholder="Tất cả trạng thái"
        show-clear
        filter
        class="toolbar-filter"
        @change="loadData"
      />
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="search" placeholder="Tìm theo email, họ tên, SĐT..." class="w-full" @input="onSearch" />
      </IconField>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text rounded
        v-tooltip.top="'Làm mới'"
        :loading="loading"
        @click="loadData"
      />
    </div>

    <!-- DataTable -->
    <div class="card">
      <DataTable
        :value="items"
        :loading="loading"
        responsive-layout="scroll"
        :paginator="true"
        :rows="pageSize"
        :total-records="total"
        :rows-per-page-options="[10, 25, 50]"
        lazy
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        @page="onPage"
        @update:rows="onRowsChange"
      >
        <template #paginatorstart>
          <span class="paginator-info" v-if="total > 0">
            Hiển thị {{ skip + 1 }}–{{ Math.min(skip + items.length, total) }} trên tổng số {{ total }} dòng
          </span>
        </template>
        <template #empty>
          <div class="empty-state">
            <i class="pi pi-users" />
            <span>Không có dữ liệu</span>
          </div>
        </template>

        <Column field="full_name"    header="Họ và tên"      sortable style="min-width: 180px" />
        <Column field="email"        header="Email"          sortable style="min-width: 200px" />
        <Column field="phone_number" header="Số điện thoại"          style="width: 140px">
          <template #body="{ data }">
            <span :class="data.phone_number ? '' : 'no-role'">{{ data.phone_number ?? '—' }}</span>
          </template>
        </Column>

        <Column header="Vai trò" style="min-width: 160px">
          <template #body="{ data }">
            <div class="role-tags">
              <div
                v-for="role in data.roles"
                :key="role.id"
                class="role-item"
              >
                <Tag
                  :value="role.name"
                  severity="info"
                  class="role-tag"
                />
                <div v-if="renderRoleScope(role)" class="role-scope-text">
                  {{ renderRoleScope(role) }}
                </div>
              </div>
              <span v-if="data.roles.length === 0" class="no-role">—</span>
            </div>
          </template>
        </Column>

        <Column field="is_active" header="Trạng thái" sortable style="width: 130px">
          <template #body="{ data }">
            <Tag
              :value="data.is_active ? 'Hoạt động' : 'Đã khóa'"
              :severity="data.is_active ? 'success' : 'danger'"
            />
          </template>
        </Column>

        <Column header="Đăng nhập cuối" style="width: 160px">
          <template #body="{ data }">
            <span class="muted-text">{{ formatDate(data.last_login_at) }}</span>
          </template>
        </Column>

        <Column header="" style="width: 130px">
          <template #body="{ data }">
            <div class="action-cell">
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text rounded size="small"
                v-tooltip.top="'Chỉnh sửa'"
                @click="openEdit(data)"
              />
              <Button
                icon="pi pi-key"
                severity="secondary"
                text rounded size="small"
                v-tooltip.top="'Đặt lại mật khẩu'"
                @click="openResetPassword(data)"
              />
              <Button
                icon="pi pi-id-card"
                severity="info"
                text rounded size="small"
                v-tooltip.top="'Quản lý vai trò'"
                @click="openRoles(data)"
              />
              <Button
                v-if="data.is_active"
                icon="pi pi-ban"
                severity="danger"
                text rounded size="small"
                v-tooltip.top="'Vô hiệu hóa'"
                @click="confirmDeactivate(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Form dialog (create / edit) -->
    <UserFormDialog
      v-model="formVisible"
      :user="editingUser"
      @saved="loadData"
    />

    <!-- Role management dialog -->
    <UserRoleDialog
      v-model="roleVisible"
      :user="roleUser"
      @changed="loadData"
    />

    <!-- Reset password dialog -->
    <Dialog
      v-model:visible="resetVisible"
      header="Đặt lại mật khẩu"
      :style="{ width: '420px' }"
      modal
      :closable="!resetting"
    >
      <div class="field">
        <label>Mật khẩu mới <span class="req">*</span></label>
        <Password
          v-model="newPassword"
          class="w-full"
          placeholder="Tối thiểu 8 ký tự, gồm chữ và số"
          :feedback="false"
          toggle-mask
          :input-style="{ width: '100%' }"
          :invalid="!!resetError"
        />
        <small v-if="resetError" class="error-msg">{{ resetError }}</small>
      </div>
      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="resetting" @click="resetVisible = false" />
        <Button label="Đặt lại" icon="pi pi-check" :loading="resetting" @click="submitResetPassword" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import UserFormDialog from './UserFormDialog.vue'
import UserRoleDialog from './UserRoleDialog.vue'
import userService, { type RoleRef, type UserListItem } from '@/services/userService'

const toast   = useToast()
const confirm = useConfirm()

// ── State ──────────────────────────────────────────────────────────────────────
const loading     = ref(false)
const items       = ref<UserListItem[]>([])
const total       = ref(0)
const skip        = ref(0)
const pageSize    = ref(10)
const search      = ref('')
const filterActive = ref<boolean | null>(null)

const formVisible  = ref(false)
const editingUser  = ref<UserListItem | null>(null)

const roleVisible  = ref(false)
const roleUser     = ref<UserListItem | null>(null)

const resetVisible = ref(false)
const resetTarget  = ref<UserListItem | null>(null)
const newPassword  = ref('')
const resetError   = ref('')
const resetting    = ref(false)

// ── Constants ──────────────────────────────────────────────────────────────────
const activeOptions = [
  { label: 'Đang hoạt động',    value: true },
  { label: 'Đã khóa',           value: false },
]

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
}

function renderRoleScope(role: RoleRef): string {
  if (role.scope_type !== 'department') return ''
  if (role.department_names && role.department_names.length > 0) {
    return `Phạm vi: ${role.department_names.join(', ')}`
  }
  if (role.department_ids && role.department_ids.length > 0) {
    return `Phạm vi: ID ${role.department_ids.join(', ')}`
  }
  return 'Phạm vi phòng ban chưa cấu hình'
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { skip.value = 0; loadData() }, 300)
}

// ── Data loading ───────────────────────────────────────────────────────────────
async function loadData() {
  loading.value = true
  try {
    const resp = await userService.list({
      search:    search.value || undefined,
      is_active: filterActive.value ?? undefined,
      skip:      skip.value,
      limit:     pageSize.value,
    })
    items.value = resp.data.items
    total.value = resp.data.total
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

function onPage(event: { first: number; rows: number }) {
  skip.value = event.first
  pageSize.value = event.rows
  loadData()
}

function onRowsChange(rows: number) {
  pageSize.value = rows
  skip.value = 0
  loadData()
}

// ── CRUD ───────────────────────────────────────────────────────────────────────
function openCreate() {
  editingUser.value = null
  formVisible.value = true
}

function openEdit(user: UserListItem) {
  editingUser.value = user
  formVisible.value = true
}

function openRoles(user: UserListItem) {
  roleUser.value   = user
  roleVisible.value = true
}

function openResetPassword(user: UserListItem) {
  resetTarget.value  = user
  newPassword.value  = ''
  resetError.value   = ''
  resetVisible.value = true
}

async function submitResetPassword() {
  if (!resetTarget.value) return
  resetError.value = ''
  if (!newPassword.value) { resetError.value = 'Mật khẩu không được để trống'; return }
  if (newPassword.value.length < 8) { resetError.value = 'Tối thiểu 8 ký tự'; return }
  if (!/[a-zA-Z]/.test(newPassword.value) || !/\d/.test(newPassword.value)) {
    resetError.value = 'Mật khẩu phải có cả chữ và số'; return
  }
  resetting.value = true
  try {
    await userService.resetPassword(resetTarget.value.id, newPassword.value)
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã đặt lại mật khẩu', life: 3000 })
    resetVisible.value = false
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    resetting.value = false
  }
}

function confirmDeactivate(user: UserListItem) {
  confirm.require({
    message:     `Vô hiệu hóa tài khoản "${user.full_name}" (${user.email})?`,
    header:      'Xác nhận vô hiệu hóa',
    icon:        'pi pi-exclamation-triangle',
    acceptLabel: 'Vô hiệu hóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await userService.deactivate(user.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã vô hiệu hóa tài khoản', life: 3000 })
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
.role-tags {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.role-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.18rem;
}

.role-tag {
  font-size: 0.75rem !important;
}

.role-scope-text {
  font-size: 0.78rem;
  line-height: 1.35;
  color: var(--l-text-muted);
}

.no-role {
  color: var(--p-text-muted-color);
}
</style>
