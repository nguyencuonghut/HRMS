<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Phòng / Ban</h2>
        <span class="subtitle">Quản lý cơ cấu phòng ban</span>
      </div>
      <Button label="Thêm mới" icon="pi pi-plus" @click="openCreate" />
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <Select
        v-model="filterActive"
        :options="activeFilterOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter"
        @change="loadData"
      />
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="searchQuery"
          placeholder="Tìm kiếm theo tên, mã..."
          class="w-full"
        />
      </IconField>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        v-tooltip.top="'Làm mới'"
        :loading="loading"
        @click="loadData"
      />
    </div>

    <!-- TreeTable -->
    <div class="card">
      <TreeTable
        :value="filteredTree"
        :loading="loading"
        v-model:expandedKeys="expandedKeys"
        responsive-layout="scroll"
        :paginator="true"
        :rows="pageRows"
        :rows-per-page-options="[10, 25, 50]"
        :first="first"
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
        @page="handlePage"
      >
        <template #paginatorstart>
          <span class="paginator-info" v-if="paginatorInfo">{{ paginatorInfo }}</span>
        </template>

        <template #empty>
          <div class="empty-state">
            <i class="pi pi-inbox" />
            <span>{{ searchQuery.trim() ? 'Không tìm thấy kết quả phù hợp' : 'Không có dữ liệu' }}</span>
          </div>
        </template>

        <Column field="name" header="Tên phòng/ban" expander style="min-width: 280px">
          <template #body="{ node }">
            <span class="dept-name">{{ node.data.name }}</span>
            <span v-if="node.data.short_name" class="short-name"> ({{ node.data.short_name }})</span>
          </template>
        </Column>

        <Column field="code" header="Mã" style="width: 120px" />

        <Column header="Loại" style="width: 120px">
          <template #body="{ node }">{{ node.data.dept_type_label }}</template>
        </Column>

        <Column header="Thứ tự" style="width: 90px">
          <template #body="{ node }">
            <span class="center-text">{{ node.data.order_no }}</span>
          </template>
        </Column>

        <Column header="Trạng thái" style="width: 130px">
          <template #body="{ node }">
            <Tag
              :value="node.data.is_active ? 'Hoạt động' : 'Đã khóa'"
              :severity="node.data.is_active ? 'success' : 'danger'"
            />
          </template>
        </Column>

        <Column header="" style="width: 100px">
          <template #body="{ node }">
            <div class="action-cell">
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text
                rounded
                size="small"
                v-tooltip.top="'Chỉnh sửa'"
                @click="openEdit(node.data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                text
                rounded
                size="small"
                v-tooltip.top="'Xóa'"
                @click="confirmDelete(node.data)"
              />
            </div>
          </template>
        </Column>
      </TreeTable>
    </div>

    <!-- Create / Edit Dialog -->
    <Dialog
      v-model:visible="dialogVisible"
      :header="editingDept ? 'Chỉnh sửa phòng/ban' : 'Thêm phòng/ban mới'"
      :style="{ width: '520px' }"
      modal
      :close-on-escape="!submitting"
      :closable="!submitting"
    >
      <form class="dept-form" @submit.prevent="submitForm">
        <!-- Mã (create only) -->
        <div v-if="!editingDept" class="field">
          <label for="f-code">Mã phòng/ban <span class="req">*</span></label>
          <InputText
            id="f-code"
            v-model="form.code"
            class="w-full"
            placeholder="VD: PHONG_KT"
            :invalid="!!errors.code"
            autocomplete="off"
          />
          <small v-if="errors.code" class="error-msg">{{ errors.code }}</small>
        </div>

        <!-- Tên đầy đủ -->
        <div class="field">
          <label for="f-name">Tên đầy đủ <span class="req">*</span></label>
          <InputText
            id="f-name"
            v-model="form.name"
            class="w-full"
            placeholder="Tên đầy đủ của phòng/ban"
            :invalid="!!errors.name"
            autocomplete="off"
          />
          <small v-if="errors.name" class="error-msg">{{ errors.name }}</small>
        </div>

        <!-- Tên viết tắt -->
        <div class="field">
          <label for="f-short">Tên viết tắt</label>
          <InputText
            id="f-short"
            v-model="form.short_name"
            class="w-full"
            placeholder="Tên rút gọn (không bắt buộc)"
            autocomplete="off"
          />
        </div>

        <!-- Loại + Thứ tự -->
        <div class="field-row">
          <div class="field">
            <label for="f-type">Loại đơn vị <span class="req">*</span></label>
            <Select
              id="f-type"
              v-model="form.dept_type"
              :options="deptTypeOptions"
              option-label="label"
              option-value="value"
              class="w-full"
            />
          </div>
          <div class="field">
            <label for="f-order">Thứ tự hiển thị</label>
            <InputNumber
              id="f-order"
              v-model="form.order_no"
              :min="0"
              :max-fraction-digits="0"
              class="w-full"
            />
          </div>
        </div>

        <!-- Phòng/ban cha -->
        <div class="field">
          <label for="f-parent">Phòng/ban cha</label>
          <Select
            id="f-parent"
            v-model="form.parent_id"
            :options="parentOptions"
            option-label="label"
            option-value="value"
            placeholder="— Không có (cấp gốc) —"
            show-clear
            class="w-full"
            filter
            filter-placeholder="Tìm kiếm..."
            empty-filter-message="Không tìm thấy"
          />
        </div>

        <!-- Trạng thái (edit only) -->
        <div v-if="editingDept" class="field field-switch">
          <label>Trạng thái</label>
          <div class="switch-row">
            <ToggleSwitch v-model="form.is_active" />
            <span :class="form.is_active ? 'active-label' : 'inactive-label'">
              {{ form.is_active ? 'Hoạt động' : 'Đã khóa' }}
            </span>
          </div>
        </div>
      </form>

      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          outlined
          :disabled="submitting"
          @click="dialogVisible = false"
        />
        <Button
          :label="editingDept ? 'Lưu thay đổi' : 'Tạo mới'"
          icon="pi pi-check"
          :loading="submitting"
          @click="submitForm"
        />
      </template>
    </Dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import TreeTable from 'primevue/treetable'

import departmentService, {
  type DepartmentRead,
  type DepartmentTreeNode,
} from '@/services/departmentService'

// ── Types ──────────────────────────────────────────────────────────────────────

interface PvTreeNode {
  key: string
  data: DepartmentRead
  children?: PvTreeNode[]
  leaf?: boolean
}

interface FormState {
  code: string
  name: string
  short_name: string
  parent_id: number | null
  dept_type: string
  order_no: number
  is_active: boolean
}

// ── State ──────────────────────────────────────────────────────────────────────

const toast   = useToast()
const confirm = useConfirm()

const loading      = ref(false)
const treeData     = ref<PvTreeNode[]>([])
const expandedKeys = ref<Record<string, boolean>>({})
const flatDepts    = ref<DepartmentRead[]>([])
const filterActive = ref<boolean | null>(null)

// Pagination & search
const searchQuery = ref('')
const first       = ref(0)
const pageRows    = ref(10)

const dialogVisible = ref(false)
const submitting    = ref(false)
const editingDept   = ref<DepartmentRead | null>(null)

const form = ref<FormState>({
  code: '', name: '', short_name: '', parent_id: null,
  dept_type: 'PHONG', order_no: 0, is_active: true,
})

const errors = ref<Partial<Record<keyof FormState, string>>>({})

// ── Constants ──────────────────────────────────────────────────────────────────

const activeFilterOptions = [
  { label: 'Tất cả trạng thái', value: null },
  { label: 'Đang hoạt động',    value: true },
  { label: 'Đã khóa',           value: false },
]

const deptTypeOptions = [
  { value: 'PHONG',   label: 'Phòng'   },
  { value: 'BAN',     label: 'Ban'     },
  { value: 'BO_PHAN', label: 'Bộ phận' },
  { value: 'NHOM',    label: 'Nhóm'   },
  { value: 'TO',      label: 'Tổ'     },
]

// ── Computed ───────────────────────────────────────────────────────────────────

const parentOptions = computed(() =>
  flatDepts.value
    .filter(d => d.id !== editingDept.value?.id)
    .map(d => ({ label: `${d.name} (${d.code})`, value: d.id }))
)

const filteredTree = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return treeData.value
  return filterNodes(treeData.value, q)
})

// Total all nodes (roots + descendants) in the current filtered view
const totalNodeCount = computed(() => countNodes(filteredTree.value))

const paginatorInfo = computed(() => {
  const total = totalNodeCount.value
  if (total === 0) return ''
  const rootTotal = filteredTree.value.length
  const from = first.value + 1
  const to   = Math.min(first.value + pageRows.value, rootTotal)
  // Show root range / total including children
  return `Hiển thị từ ${from} đến ${to} dòng trên tổng số ${total} dòng`
})

// ── Helpers ────────────────────────────────────────────────────────────────────

function filterNodes(nodes: PvTreeNode[], q: string): PvTreeNode[] {
  const result: PvTreeNode[] = []
  for (const node of nodes) {
    const hit = node.data.name.toLowerCase().includes(q) || node.data.code.toLowerCase().includes(q)
    const children = filterNodes(node.children ?? [], q)
    if (hit || children.length) result.push({ ...node, children })
  }
  return result
}

function countNodes(nodes: PvTreeNode[]): number {
  return nodes.reduce((sum, n) => sum + 1 + countNodes(n.children ?? []), 0)
}

function toTreeNodes(nodes: DepartmentTreeNode[]): PvTreeNode[] {
  return nodes.map(n => ({
    key:      String(n.id),
    data:     n as DepartmentRead,
    children: n.children.length ? toTreeNodes(n.children) : undefined,
    leaf:     n.children.length === 0,
  }))
}

function collectExpandedKeys(nodes: PvTreeNode[]): Record<string, boolean> {
  const keys: Record<string, boolean> = {}
  const walk = (list: PvTreeNode[]) => {
    for (const node of list) {
      if (node.children?.length) { keys[node.key] = true; walk(node.children) }
    }
  }
  walk(nodes)
  return keys
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

// ── Watchers ───────────────────────────────────────────────────────────────────

// Reset to page 1 and re-expand when search changes
watch(searchQuery, () => {
  first.value = 0
  expandedKeys.value = collectExpandedKeys(filteredTree.value)
})

// ── Pagination ─────────────────────────────────────────────────────────────────

function handlePage(e: { first: number; rows: number }) {
  first.value    = e.first
  pageRows.value = e.rows
}

// ── Data loading ───────────────────────────────────────────────────────────────

async function loadData() {
  loading.value = true
  try {
    const [treeRes, flatRes] = await Promise.all([
      departmentService.getTree(filterActive.value ?? undefined),
      departmentService.getList(),
    ])
    treeData.value     = toTreeNodes(treeRes.data)
    expandedKeys.value = collectExpandedKeys(treeData.value)
    flatDepts.value    = flatRes.data
    first.value        = 0
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loading.value = false
  }
}

// ── CRUD actions ───────────────────────────────────────────────────────────────

function openCreate() {
  editingDept.value = null
  form.value = { code: '', name: '', short_name: '', parent_id: null, dept_type: 'PHONG', order_no: 0, is_active: true }
  errors.value = {}
  dialogVisible.value = true
}

function openEdit(dept: DepartmentRead) {
  editingDept.value = dept
  form.value = {
    code:       dept.code,
    name:       dept.name,
    short_name: dept.short_name ?? '',
    parent_id:  dept.parent_id,
    dept_type:  dept.dept_type,
    order_no:   dept.order_no,
    is_active:  dept.is_active,
  }
  errors.value = {}
  dialogVisible.value = true
}

function validate(): boolean {
  errors.value = {}
  if (!editingDept.value && !form.value.code.trim()) {
    errors.value.code = 'Mã phòng/ban không được để trống'
  }
  if (!form.value.name.trim()) {
    errors.value.name = 'Tên phòng/ban không được để trống'
  }
  return Object.keys(errors.value).length === 0
}

async function submitForm() {
  if (!validate()) return
  submitting.value = true
  try {
    const shortName = form.value.short_name.trim() || null

    if (editingDept.value) {
      await departmentService.update(editingDept.value.id, {
        name:       form.value.name.trim(),
        short_name: shortName,
        parent_id:  form.value.parent_id ?? null,
        dept_type:  form.value.dept_type,
        order_no:   form.value.order_no ?? 0,
        is_active:  form.value.is_active,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật phòng/ban', life: 3000 })
    } else {
      await departmentService.create({
        code:       form.value.code.trim(),
        name:       form.value.name.trim(),
        short_name: shortName,
        parent_id:  form.value.parent_id ?? null,
        dept_type:  form.value.dept_type,
        order_no:   form.value.order_no ?? 0,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo phòng/ban mới', life: 3000 })
    }

    dialogVisible.value = false
    await loadData()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

function confirmDelete(dept: DepartmentRead) {
  confirm.require({
    message:      `Bạn có chắc chắn muốn xóa phòng/ban "${dept.name}"?`,
    header:       'Xác nhận xóa',
    icon:         'pi pi-exclamation-triangle',
    acceptLabel:  'Xóa',
    rejectLabel:  'Hủy',
    acceptClass:  'p-button-danger',
    accept: async () => {
      try {
        const res = await departmentService.delete(dept.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: res.data.message, life: 3000 })
        await loadData()
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
      }
    },
  })
}

// ── Lifecycle ──────────────────────────────────────────────────────────────────

onMounted(loadData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem;

  h2 { margin: 0 0 0.2rem; font-size: 1.5rem; font-weight: 700; }
  .subtitle { color: var(--p-text-muted-color); font-size: 0.875rem; }
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.toolbar-filter { min-width: 180px; }
.toolbar-search { min-width: 260px; }

@media (max-width: 640px) {
  .toolbar-search {
    flex: 1 1 100%;
    min-width: 0;
    order: 1;
  }
  .toolbar-filter {
    flex: 1;
    min-width: 0;
    order: 2;
  }
}

.card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
  overflow: hidden;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem;
  color: var(--p-text-muted-color);
  i { font-size: 2rem; opacity: 0.3; }
}

.paginator-info {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.dept-name { font-weight: 500; }
.short-name { color: var(--p-text-muted-color); font-size: 0.85em; }
.center-text { display: block; text-align: center; }

.action-cell {
  display: flex;
  gap: 0.25rem;
  justify-content: flex-end;
}

/* Dialog form */
.dept-form { display: flex; flex-direction: column; gap: 0.1rem; }

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 1rem;

  label { font-weight: 500; font-size: 0.875rem; }
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;

  .field { margin-bottom: 0; }
}

.field-switch label { font-weight: 500; font-size: 0.875rem; }

.switch-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.active-label   { color: var(--p-green-600); font-size: 0.875rem; font-weight: 500; }
.inactive-label { color: var(--p-red-500);   font-size: 0.875rem; font-weight: 500; }

.req { color: var(--p-red-500); margin-left: 2px; }

.error-msg {
  color: var(--p-red-500);
  font-size: 0.8rem;
  margin-top: -0.2rem;
}

.w-full { width: 100%; }
</style>
