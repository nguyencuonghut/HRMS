<template>
  <Dialog
    v-model:visible="visible"
    :header="`Quản lý vai trò — ${user?.full_name ?? ''}`"
    :style="{ width: '640px' }"
    modal
    @show="onShow"
  >
    <div v-if="loading" class="loading-state">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <template v-else>
      <!-- Current roles -->
      <div class="section-title">Vai trò hiện tại</div>
      <div v-if="currentRoles.length === 0" class="empty-roles">Chưa có vai trò nào</div>
      <div v-else class="current-roles">
        <div v-for="role in currentRoles" :key="role.id" class="role-card">
          <div class="role-card-header">
            <div class="role-chip-content">
              <Tag :value="role.name" severity="info" class="role-tag" />
              <div v-if="renderRoleScope(role)" class="role-scope">
                {{ renderRoleScope(role) }}
              </div>
            </div>
            <div class="role-card-actions">
              <Button
                v-if="canEditRoleScope(role)"
                :label="editingRoleScope?.id === role.id ? 'Đang sửa' : 'Đổi phòng ban'"
                icon="pi pi-pencil"
                severity="secondary"
                text
                size="small"
                :disabled="assigning && editingRoleScope?.id === role.id"
                @click="beginEditRoleScope(role)"
              />
              <Button
                icon="pi pi-times"
                severity="danger"
                text
                rounded
                size="small"
                v-tooltip.top="'Gỡ vai trò'"
                :loading="removingId === role.id"
                @click="removeRole(role)"
              />
            </div>
          </div>

          <div v-if="editingRoleScope?.id === role.id" class="role-scope-editor">
            <label class="scope-label" :for="`edit-role-scope-departments-${role.id}`">
              Phòng ban được quản lý <span class="req">*</span>
            </label>
            <MultiSelect
              :id="`edit-role-scope-departments-${role.id}`"
              v-model="editingDepartmentIds"
              :options="departmentOptions"
              option-label="plain_name"
              option-value="id"
              placeholder="Chọn một hoặc nhiều phòng ban"
              filter
              display="chip"
              class="scope-select"
              :loading="departmentsLoading"
            />
            <small class="scope-help">
              Role `Quản lý phòng ban` chỉ được thao tác trong các phòng ban đã gán và toàn bộ đơn vị con của chúng.
            </small>
            <div class="role-scope-editor-actions">
              <Button
                label="Hủy"
                severity="secondary"
                outlined
                @click="cancelEditRoleScope"
              />
              <Button
                label="Lưu phạm vi"
                icon="pi pi-check"
                :loading="assigning"
                @click="saveEditedRoleScope"
              />
            </div>
          </div>
        </div>
      </div>

      <Divider />

      <!-- Assign new role -->
      <div class="section-title">Gán vai trò mới</div>
      <div class="assign-row">
        <Select
          v-model="selectedRole"
          :options="availableRoles"
          option-label="name"
          option-value="id"
          placeholder="Chọn vai trò"
          filter
          class="role-select"
          :loading="rolesLoading"
        />
        <Button
          label="Gán"
          icon="pi pi-plus"
          :disabled="!selectedRole"
          :loading="assigning"
          @click="assignRole"
        />
      </div>

      <div v-if="selectedRoleRequiresDepartmentScope" class="scope-panel">
        <label class="scope-label" for="role-scope-departments">Phòng ban được quản lý <span class="req">*</span></label>
        <MultiSelect
          id="role-scope-departments"
          v-model="selectedDepartmentIds"
          :options="departmentOptions"
          option-label="plain_name"
          option-value="id"
          placeholder="Chọn một hoặc nhiều phòng ban"
          filter
          display="chip"
          class="scope-select"
          :loading="departmentsLoading"
        />
        <small class="scope-help">
          Role `Quản lý phòng ban` chỉ được thao tác trong các phòng ban đã gán và toàn bộ đơn vị con của chúng.
        </small>
      </div>
    </template>

    <template #footer>
      <Button label="Đóng" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import api from '@/services/api'
import userService, { type RoleRef, type UserListItem } from '@/services/userService'
import departmentService, { type DepartmentOption } from '@/services/departmentService'

interface RoleOption { id: number; code: string; name: string }

const props = defineProps<{ user: UserListItem | null }>()
const emit  = defineEmits<{ (e: 'changed'): void }>()

const visible      = defineModel<boolean>({ required: true })
const toast        = useToast()
const loading      = ref(false)
const rolesLoading = ref(false)
const departmentsLoading = ref(false)
const assigning    = ref(false)
const removingId   = ref<number | null>(null)

const currentRoles = ref<RoleRef[]>([])
const allRoles     = ref<RoleOption[]>([])
const departmentOptions = ref<DepartmentOption[]>([])
const selectedRole = ref<number | null>(null)
const selectedDepartmentIds = ref<number[]>([])
const editingRoleScope = ref<RoleRef | null>(null)
const editingDepartmentIds = ref<number[]>([])

const availableRoles = computed(() =>
  allRoles.value.filter(r => !currentRoles.value.some(cr => cr.id === r.id))
)

const selectedRoleOption = computed(() =>
  allRoles.value.find(role => role.id === selectedRole.value) ?? null
)

const selectedRoleRequiresDepartmentScope = computed(() =>
  selectedRoleOption.value?.code === 'line_manager'
)

watch(selectedRoleRequiresDepartmentScope, (requiresScope) => {
  if (!requiresScope) selectedDepartmentIds.value = []
})

async function onShow() {
  if (!props.user) return
  loading.value = true
  rolesLoading.value = true
  departmentsLoading.value = true
  selectedRole.value = null
  selectedDepartmentIds.value = []
  editingRoleScope.value = null
  editingDepartmentIds.value = []
  try {
    const [rolesRes, allRes, departmentsRes] = await Promise.all([
      userService.getRoles(props.user.id),
      api.get<RoleOption[]>('/roles'),
      departmentService.getList(true),
    ])
    currentRoles.value = rolesRes.data
    allRoles.value     = allRes.data
    departmentOptions.value = departmentsRes.data
  } finally {
    loading.value = false
    rolesLoading.value = false
    departmentsLoading.value = false
  }
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi'
}

async function assignRole() {
  if (!props.user || !selectedRole.value) return
  if (selectedRoleRequiresDepartmentScope.value && selectedDepartmentIds.value.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'Thiếu phạm vi phòng ban',
      detail: 'Vai trò Quản lý phòng ban bắt buộc phải gán ít nhất 1 phòng ban.',
      life: 4000,
    })
    return
  }
  assigning.value = true
  try {
    await userService.assignRole(props.user.id, {
      role_id: selectedRole.value,
      scope_type: selectedRoleRequiresDepartmentScope.value ? 'department' : undefined,
      department_ids: selectedRoleRequiresDepartmentScope.value
        ? selectedDepartmentIds.value
        : undefined,
    })
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã gán vai trò', life: 3000 })
    selectedRole.value = null
    selectedDepartmentIds.value = []
    emit('changed')
    await onShow()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    assigning.value = false
  }
}

async function saveEditedRoleScope() {
  if (!props.user || !editingRoleScope.value) return
  if (editingDepartmentIds.value.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'Thiếu phạm vi phòng ban',
      detail: 'Vai trò Quản lý phòng ban bắt buộc phải gán ít nhất 1 phòng ban.',
      life: 4000,
    })
    return
  }
  assigning.value = true
  try {
    await userService.assignRole(props.user.id, {
      role_id: editingRoleScope.value.id,
      scope_type: 'department',
      department_ids: editingDepartmentIds.value,
    })
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật phạm vi vai trò', life: 3000 })
    cancelEditRoleScope()
    emit('changed')
    await onShow()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    assigning.value = false
  }
}

async function removeRole(role: RoleRef) {
  if (!props.user) return
  removingId.value = role.id
  try {
    await userService.removeRole(props.user.id, role.id)
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã gỡ vai trò', life: 3000 })
    emit('changed')
    await onShow()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    removingId.value = null
  }
}

function renderRoleScope(role: RoleRef): string {
  if (role.scope_type !== 'department') return ''
  if (role.department_names && role.department_names.length > 0) {
    return `Phạm vi: ${role.department_names.join(', ')}`
  }
  if (role.department_ids && role.department_ids.length > 0) {
    return `Phạm vi: ID ${role.department_ids.join(', ')}`
  }
  return 'Phạm vi phòng ban chưa được cấu hình'
}

function canEditRoleScope(role: RoleRef): boolean {
  return role.code === 'line_manager'
}

function beginEditRoleScope(role: RoleRef) {
  editingRoleScope.value = role
  editingDepartmentIds.value = [...(role.department_ids ?? [])]
}

function cancelEditRoleScope() {
  editingRoleScope.value = null
  editingDepartmentIds.value = []
}
</script>

<style scoped>
.loading-state {
  display: flex; justify-content: center; padding: 2rem;
  color: var(--p-text-muted-color);
}

.section-title {
  font-weight: 600; font-size: 0.875rem;
  color: var(--p-text-muted-color);
  text-transform: uppercase; letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.empty-roles {
  color: var(--p-text-muted-color); font-size: 0.875rem;
  padding: 0.5rem 0; margin-bottom: 0.5rem;
}

.current-roles {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.role-card {
  padding: 0.875rem 1rem;
  border: 1px solid var(--l-border);
  border-radius: 0.875rem;
  background: color-mix(in srgb, var(--l-surface-variant) 82%, var(--l-surface) 18%);
  color: var(--l-text);
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 4%, transparent);
}

.role-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.role-card-actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
}

.role-chip-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.role-tag {
  align-self: flex-start;
}

.role-tag:deep(.p-tag) {
  background: color-mix(in srgb, var(--p-primary-color) 18%, var(--l-surface));
  color: var(--p-primary-color);
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 34%, transparent);
  font-weight: 600;
}

.role-scope {
  font-size: 0.8125rem;
  color: var(--l-text-muted);
}

.role-card-actions :deep(.p-button.p-button-text.p-button-secondary),
.role-card-actions :deep(.p-button.p-button-text.p-button-secondary .p-button-label),
.role-card-actions :deep(.p-button.p-button-text.p-button-secondary .p-button-icon) {
  color: var(--l-text) !important;
}

.role-card-actions :deep(.p-button.p-button-text.p-button-secondary:hover) {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}

.role-card-actions :deep(.p-button.p-button-text.p-button-danger),
.role-card-actions :deep(.p-button.p-button-text.p-button-danger .p-button-icon) {
  color: var(--p-red-400) !important;
}

.role-card-actions :deep(.p-button.p-button-text.p-button-danger:hover) {
  background: color-mix(in srgb, var(--p-red-500) 12%, transparent);
}

.assign-row {
  display: flex; gap: 0.75rem; align-items: center;
}

.role-select { flex: 1; }

.scope-panel {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.scope-label {
  font-size: 0.875rem;
  font-weight: 600;
}

.scope-select {
  width: 100%;
}

.scope-help {
  color: var(--l-text-muted);
  line-height: 1.45;
}

.role-scope-editor {
  margin-top: 0.875rem;
  padding-top: 0.875rem;
  border-top: 1px dashed var(--p-content-border-color);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.role-scope-editor-actions {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.req {
  color: var(--p-red-400);
}

@media (max-width: 768px) {
  .assign-row {
    flex-direction: column;
    align-items: stretch;
  }

  .role-card-header,
  .role-scope-editor-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .role-card-actions {
    justify-content: flex-end;
  }
}
</style>
