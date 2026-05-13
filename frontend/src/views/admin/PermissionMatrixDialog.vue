<template>
  <Dialog
    v-model:visible="visible"
    :header="`Ma trận quyền — ${role?.name ?? ''}`"
    :style="{ width: '820px', maxWidth: '95vw' }"
    modal
    :close-on-escape="!saving"
    :closable="!saving"
    @show="onShow"
  >
    <div v-if="loading" class="loading-state">
      <i class="pi pi-spin pi-spinner" />
      <span>Đang tải...</span>
    </div>

    <template v-else>
      <div class="matrix-wrap">
        <table class="matrix-table">
          <thead>
            <tr>
              <th class="module-col">Module</th>
              <th v-for="action in ACTIONS" :key="action.key" class="action-col">
                {{ action.label }}
              </th>
              <th class="action-col all-col">Tất cả</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="mod in MODULES" :key="mod.key">
              <td class="module-name">{{ mod.label }}</td>
              <td
                v-for="action in ACTIONS"
                :key="action.key"
                class="check-cell"
              >
                <Checkbox
                  v-if="permMap[mod.key]?.[action.key]"
                  :model-value="isChecked(mod.key, action.key)"
                  :binary="true"
                  @update:model-value="toggle(mod.key, action.key)"
                />
                <span v-else class="no-perm">—</span>
              </td>
              <td class="check-cell all-col">
                <Checkbox
                  :model-value="isRowAll(mod.key)"
                  :binary="true"
                  @update:model-value="toggleRow(mod.key)"
                />
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td class="module-name footer-label">Tất cả</td>
              <td v-for="action in ACTIONS" :key="action.key" class="check-cell">
                <Checkbox
                  :model-value="isColAll(action.key)"
                  :binary="true"
                  @update:model-value="toggleCol(action.key)"
                />
              </td>
              <td class="check-cell all-col">
                <Checkbox
                  :model-value="isAllChecked"
                  :binary="true"
                  @update:model-value="toggleAll"
                />
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div class="summary">
        <span class="muted">Đã chọn {{ selectedIds.size }} / {{ totalPerms }} quyền</span>
      </div>
    </template>

    <template #footer>
      <Button label="Hủy" severity="secondary" outlined :disabled="saving" @click="visible = false" />
      <Button label="Lưu" icon="pi pi-check" :loading="saving" @click="save" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import roleService, { type PermissionRead, type RoleListItem } from '@/services/roleService'

const props = defineProps<{ role: RoleListItem | null }>()
const emit  = defineEmits<{ (e: 'saved'): void }>()

const visible = defineModel<boolean>({ required: true })
const toast   = useToast()
const loading = ref(false)
const saving  = ref(false)

// ── Constants ──────────────────────────────────────────────────────────────────

const MODULES = [
  { key: 'org',         label: 'Cơ cấu tổ chức' },
  { key: 'employees',   label: 'Nhân sự' },
  { key: 'contracts',   label: 'Hợp đồng' },
  { key: 'leaves',      label: 'Nghỉ phép' },
  { key: 'insurance',   label: 'Bảo hiểm BHXH' },
  { key: 'salary',      label: 'Lương BHXH' },
  { key: 'rewards',     label: 'Khen thưởng' },
  { key: 'training',    label: 'Đào tạo' },
  { key: 'performance', label: 'Đánh giá KPI' },
  { key: 'reports',     label: 'Báo cáo' },
  { key: 'users',       label: 'Người dùng' },
  { key: 'roles',       label: 'Vai trò' },
  { key: 'audit_logs',  label: 'Nhật ký hệ thống' },
]

const ACTIONS = [
  { key: 'view',   label: 'Xem' },
  { key: 'create', label: 'Thêm' },
  { key: 'edit',   label: 'Sửa' },
  { key: 'delete', label: 'Xóa' },
  { key: 'export', label: 'Xuất' },
]

// ── State ──────────────────────────────────────────────────────────────────────

// permMap[module][action] = permission id (hay undefined nếu không tồn tại)
const permMap    = ref<Record<string, Record<string, number>>>({})
const selectedIds = ref<Set<number>>(new Set())
const totalPerms  = ref(0)

// ── Computed helpers ───────────────────────────────────────────────────────────

function isChecked(mod: string, action: string): boolean {
  const id = permMap.value[mod]?.[action]
  return id !== undefined && selectedIds.value.has(id)
}

function isRowAll(mod: string): boolean {
  const actions = permMap.value[mod]
  if (!actions) return false
  return Object.values(actions).every(id => selectedIds.value.has(id))
}

function isColAll(action: string): boolean {
  return MODULES.every(m => {
    const id = permMap.value[m.key]?.[action]
    return id === undefined || selectedIds.value.has(id)
  })
}

const isAllChecked = computed(() =>
  MODULES.every(m => isRowAll(m.key))
)

// ── Toggle helpers ─────────────────────────────────────────────────────────────

function toggle(mod: string, action: string) {
  const id = permMap.value[mod]?.[action]
  if (id === undefined) return
  const set = new Set(selectedIds.value)
  if (set.has(id)) set.delete(id)
  else set.add(id)
  selectedIds.value = set
}

function toggleRow(mod: string) {
  const actions = permMap.value[mod]
  if (!actions) return
  const set   = new Set(selectedIds.value)
  const allOn = Object.values(actions).every(id => set.has(id))
  for (const id of Object.values(actions)) {
    if (allOn) set.delete(id)
    else set.add(id)
  }
  selectedIds.value = set
}

function toggleCol(action: string) {
  const set   = new Set(selectedIds.value)
  const ids   = MODULES.map(m => permMap.value[m.key]?.[action]).filter((id): id is number => id !== undefined)
  const allOn = ids.every(id => set.has(id))
  for (const id of ids) {
    if (allOn) set.delete(id)
    else set.add(id)
  }
  selectedIds.value = set
}

function toggleAll(val: boolean) {
  const set = new Set<number>()
  if (val) {
    for (const mod of Object.values(permMap.value)) {
      for (const id of Object.values(mod)) set.add(id)
    }
  }
  selectedIds.value = set
}

// ── Load & save ────────────────────────────────────────────────────────────────

async function onShow() {
  if (!props.role) return
  loading.value = true
  try {
    const [allRes, curRes] = await Promise.all([
      roleService.listAllPermissions(),
      roleService.getPermissions(props.role.id),
    ])

    const map: Record<string, Record<string, number>> = {}
    let count = 0
    for (const p of allRes.data) {
      if (!map[p.module]) map[p.module] = {}
      map[p.module][p.action] = p.id
      count++
    }
    permMap.value  = map
    totalPerms.value = count

    const cur = new Set(curRes.data.map((p: PermissionRead) => p.id))
    selectedIds.value = cur
  } finally {
    loading.value = false
  }
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const d = err.response?.data?.detail
  return typeof d === 'string' ? d : 'Đã xảy ra lỗi'
}

async function save() {
  if (!props.role) return
  saving.value = true
  try {
    await roleService.replacePermissions(props.role.id, [...selectedIds.value])
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã lưu ma trận quyền', life: 3000 })
    visible.value = false
    emit('saved')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.loading-state {
  display: flex; align-items: center; justify-content: center;
  gap: 0.75rem; padding: 2rem; color: var(--p-text-muted-color);
}

.matrix-wrap {
  overflow-x: auto;
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.matrix-table th,
.matrix-table td {
  border: 1px solid var(--p-content-border-color);
  padding: 0.5rem 0.75rem;
}

.matrix-table thead th {
  background: var(--p-surface-100);
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
}

.module-col  { text-align: left; min-width: 160px; }
.action-col  { width: 72px; text-align: center; }
.all-col     { background: var(--p-surface-50); }

.module-name {
  font-weight: 500;
  color: var(--p-text-color);
}

.footer-label {
  font-weight: 600;
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
  text-transform: uppercase;
}

.check-cell {
  text-align: center;
  vertical-align: middle;
}

.no-perm { color: var(--p-text-muted-color); font-size: 0.75rem; }

.summary {
  margin-top: 0.75rem;
  text-align: right;
}

.muted { color: var(--p-text-muted-color); font-size: 0.875rem; }
</style>
