<template>
  <Dialog
    v-model:visible="visible"
    :header="`Quản lý vai trò — ${user?.full_name ?? ''}`"
    :style="{ width: '520px' }"
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
        <div v-for="role in currentRoles" :key="role.id" class="role-chip">
          <Tag :value="role.name" severity="info" />
          <Button
            icon="pi pi-times"
            severity="danger"
            text rounded size="small"
            v-tooltip.top="'Gỡ vai trò'"
            :loading="removingId === role.id"
            @click="removeRole(role)"
          />
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
    </template>

    <template #footer>
      <Button label="Đóng" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import api from '@/services/api'
import userService, { type RoleRef, type UserListItem } from '@/services/userService'

interface RoleOption { id: number; code: string; name: string }

const props = defineProps<{ user: UserListItem | null }>()
const emit  = defineEmits<{ (e: 'changed'): void }>()

const visible      = defineModel<boolean>({ required: true })
const toast        = useToast()
const loading      = ref(false)
const rolesLoading = ref(false)
const assigning    = ref(false)
const removingId   = ref<number | null>(null)

const currentRoles = ref<RoleRef[]>([])
const allRoles     = ref<RoleOption[]>([])
const selectedRole = ref<number | null>(null)

const availableRoles = computed(() =>
  allRoles.value.filter(r => !currentRoles.value.some(cr => cr.id === r.id))
)

async function onShow() {
  if (!props.user) return
  loading.value = true
  rolesLoading.value = true
  try {
    const [rolesRes, allRes] = await Promise.all([
      userService.getRoles(props.user.id),
      api.get<RoleOption[]>('/roles'),
    ])
    currentRoles.value = rolesRes.data
    allRoles.value     = allRes.data
  } finally {
    loading.value = false
    rolesLoading.value = false
  }
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi'
}

async function assignRole() {
  if (!props.user || !selectedRole.value) return
  assigning.value = true
  try {
    await userService.assignRole(props.user.id, { role_id: selectedRole.value })
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã gán vai trò', life: 3000 })
    selectedRole.value = null
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
  display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.5rem;
}

.role-chip {
  display: flex; align-items: center; gap: 0.25rem;
}

.assign-row {
  display: flex; gap: 0.75rem; align-items: center;
}

.role-select { flex: 1; }
</style>
