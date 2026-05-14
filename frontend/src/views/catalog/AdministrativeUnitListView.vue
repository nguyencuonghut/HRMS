<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h2>Danh mục hành chính</h2>
        <span class="subtitle">Quản trị đơn vị hành chính và xem cây phân cấp dữ liệu địa chỉ</span>
      </div>
      <div class="header-actions">
        <Button
          label="Lịch sử import"
          icon="pi pi-history"
          severity="secondary"
          outlined
          @click="router.push('/catalog/administrative-imports')"
        />
        <Button
          label="Import dữ liệu"
          icon="pi pi-download"
          severity="contrast"
          :loading="importing"
          @click="importDialogVisible = true"
        />
        <Button label="Thêm mới" icon="pi pi-plus" @click="openCreate" />
      </div>
    </div>

    <div class="toolbar">
      <Select
        v-model="systemType"
        :options="systemOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter"
        @change="handleSystemOrStateChange"
      />
      <Select
        v-model="filterActive"
        :options="activeOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter"
        @change="handleSystemOrStateChange"
      />
      <Select
        v-model="filterUnitType"
        :options="unitTypeOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter"
      />
      <Select
        v-model="filterProvinceCode"
        :options="provinceOptions"
        option-label="label"
        option-value="value"
        class="toolbar-filter"
        placeholder="Lọc theo tỉnh"
        show-clear
        filter
      />
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="listSearchQuery"
          class="w-full"
          placeholder="Tìm theo tên hoặc mã..."
          @input="onListSearch"
          @keydown.enter="triggerListSearch"
        />
      </IconField>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loadingList || loadingTree"
        v-tooltip.top="'Làm mới'"
        @click="refreshView"
      />
    </div>

    <div class="content-grid">
      <div class="card">
        <div class="card-header">
          <div>
            <h3>Cây phân cấp</h3>
            <span class="muted">Hiển thị theo hệ hành chính đã chọn</span>
          </div>
        </div>

        <TreeTable
          :value="treeData"
          :loading="loadingTree"
          v-model:expandedKeys="expandedKeys"
          responsive-layout="scroll"
          @node-expand="handleNodeExpand"
        >
          <template #empty>
            <div class="empty-state">
              <i class="pi pi-inbox" />
              <span>{{ systemType === 'old' ? 'Hệ cũ chưa được triển khai dữ liệu' : 'Không có dữ liệu cây' }}</span>
            </div>
          </template>

          <Column field="name" header="Tên đơn vị" expander style="min-width: 280px">
            <template #body="{ node }">
              <div class="tree-name">
                <span>{{ node.data.name }}</span>
                <small>{{ typeLabel(node.data.unit_type) }}</small>
              </div>
            </template>
          </Column>
          <Column field="code" header="Mã" style="width: 130px" />
          <Column field="province_code" header="Tỉnh" style="width: 150px" />
          <Column field="is_active" header="Trạng thái" style="width: 120px">
            <template #body="{ node }">
              <Tag
                :value="node.data.is_active ? 'Hoạt động' : 'Đã khóa'"
                :severity="node.data.is_active ? 'success' : 'danger'"
              />
            </template>
          </Column>
        </TreeTable>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h3>Danh sách quản trị</h3>
            <span class="muted">Tạo, sửa, khóa đơn vị hành chính</span>
          </div>
        </div>

        <DataTable
          :value="units"
          :loading="loadingList"
          stripedRows
          paginator
          lazy
          responsive-layout="scroll"
          :rows="listPageSize"
          :first="(listPage - 1) * listPageSize"
          :total-records="totalUnits"
          :rows-per-page-options="[10, 25, 50]"
          paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
          @page="onListPage"
        >
          <template #paginatorstart>
            <span class="paginator-info" v-if="totalUnits > 0">
              Hiển thị {{ (listPage - 1) * listPageSize + 1 }}–{{ Math.min((listPage - 1) * listPageSize + units.length, totalUnits) }}
              trên tổng số {{ totalUnits }} dòng
            </span>
          </template>
          <template #empty>
            <div class="empty-state">
              <i class="pi pi-inbox" />
              <span>Không có dữ liệu phù hợp</span>
            </div>
          </template>

          <Column field="name" header="Tên" style="min-width: 220px" />
          <Column field="code" header="Mã" style="width: 120px" />
          <Column field="unit_type" header="Loại" style="width: 110px">
            <template #body="{ data }">{{ typeLabel(data.unit_type) }}</template>
          </Column>
          <Column field="province_code" header="Mã tỉnh" style="width: 130px">
            <template #body="{ data }">{{ data.province_code || '—' }}</template>
          </Column>
          <Column field="source_name" header="Nguồn" style="width: 130px">
            <template #body="{ data }">{{ data.source_name || 'manual' }}</template>
          </Column>
          <Column field="is_active" header="Trạng thái" style="width: 120px">
            <template #body="{ data }">
              <Tag
                :value="data.is_active ? 'Hoạt động' : 'Đã khóa'"
                :severity="data.is_active ? 'success' : 'danger'"
              />
            </template>
          </Column>
          <Column header="" style="width: 110px">
            <template #body="{ data }">
              <div class="action-cell">
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  size="small"
                  v-tooltip.top="'Chỉnh sửa'"
                  @click="openEdit(data)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  size="small"
                  v-tooltip.top="'Khóa'"
                  @click="confirmDelete(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <Dialog
      v-model:visible="dialogVisible"
      :header="editingUnit ? 'Chỉnh sửa đơn vị hành chính' : 'Thêm đơn vị hành chính'"
      :style="{ width: '560px' }"
      modal
      :close-on-escape="!submitting"
      :closable="!submitting"
    >
      <form class="form-shell" @submit.prevent="submitForm">
        <div v-if="!editingUnit" class="field">
          <label for="f-code">Mã đơn vị <span class="req">*</span></label>
          <InputText id="f-code" v-model="form.code" class="w-full" :invalid="!!errors.code" />
          <small v-if="errors.code" class="error-msg">{{ errors.code }}</small>
        </div>

        <div class="field">
          <label for="f-name">Tên đơn vị <span class="req">*</span></label>
          <InputText id="f-name" v-model="form.name" class="w-full" :invalid="!!errors.name" />
          <small v-if="errors.name" class="error-msg">{{ errors.name }}</small>
        </div>

        <div class="field-row">
          <div class="field">
            <label for="f-type">Loại đơn vị <span class="req">*</span></label>
            <Select
              id="f-type"
              v-model="form.unit_type"
              :options="creatableUnitTypeOptions"
              option-label="label"
              option-value="value"
              class="w-full"
              :disabled="!!editingUnit"
            />
          </div>
          <div class="field">
            <label for="f-province">Tỉnh/Thành phố</label>
            <Select
              id="f-province"
              v-model="form.province_code"
              :options="provinceOptions"
              option-label="label"
              option-value="value"
              class="w-full"
              show-clear
              filter
              placeholder="Chọn tỉnh/thành"
              :disabled="form.unit_type === 'province'"
            />
          </div>
        </div>

        <div class="field">
          <label for="f-official-name">Tên chính thức</label>
          <InputText id="f-official-name" v-model="form.official_name" class="w-full" />
        </div>

        <div v-if="editingUnit" class="field field-switch">
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
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="dialogVisible = false" />
        <Button :label="editingUnit ? 'Lưu thay đổi' : 'Tạo mới'" icon="pi pi-check" :loading="submitting" @click="submitForm" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="importDialogVisible"
      header="Import dữ liệu hành chính"
      :style="{ width: '520px' }"
      modal
      :close-on-escape="!importing"
      :closable="!importing"
    >
      <form class="form-shell" @submit.prevent="submitImport">
        <div class="field-row">
          <div class="field">
            <label for="i-system">Hệ hành chính</label>
            <Select
              id="i-system"
              v-model="importForm.system_type"
              :options="systemOptions"
              option-label="label"
              option-value="value"
              class="w-full"
            />
          </div>
          <div class="field">
            <label for="i-mode">Chế độ import</label>
            <Select
              id="i-mode"
              v-model="importForm.mode"
              :options="importModeOptions"
              option-label="label"
              option-value="value"
              class="w-full"
            />
          </div>
        </div>

        <div class="field">
          <label for="i-source">Nguồn dữ liệu</label>
          <InputText id="i-source" v-model="importForm.source_name" class="w-full" />
        </div>

        <div class="field">
          <label for="i-version">Phiên bản nguồn</label>
          <InputText id="i-version" v-model="importForm.source_version" class="w-full" />
        </div>

        <div class="hint-box">
          Import hiện tại dùng nguồn JSON mặc định đã cấu hình ở backend. Màn này phù hợp cho thao tác đồng bộ lại dữ liệu chính thức.
        </div>
      </form>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="importing" @click="importDialogVisible = false" />
        <Button label="Chạy import" icon="pi pi-download" :loading="importing" @click="submitImport" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import TreeTable from 'primevue/treetable'

import administrativeUnitService, { type AdministrativeUnitRead } from '@/services/administrativeUnitService'

interface PvTreeNode {
  key: string
  data: AdministrativeUnitRead
  children?: PvTreeNode[]
  leaf?: boolean
}

interface FormState {
  code: string
  name: string
  unit_type: 'province' | 'district' | 'ward'
  official_name: string
  province_code: string | null
  is_active: boolean
}

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const loadingList = ref(false)
const loadingTree = ref(false)
const importing = ref(false)
const submitting = ref(false)

const units = ref<AdministrativeUnitRead[]>([])
const totalUnits = ref(0)
const provinces = ref<AdministrativeUnitRead[]>([])
const treeData = ref<PvTreeNode[]>([])
const expandedKeys = ref<Record<string, boolean>>({})
const provinceCache = new Map<string, AdministrativeUnitRead[]>()

const systemType = ref<'old' | 'new'>('new')
const filterActive = ref<boolean | null>(true)
const filterUnitType = ref<string | null>(null)
const filterProvinceCode = ref<string | null>(null)
const listSearchQuery = ref('')
const listPage = ref(1)
const listPageSize = ref(10)
let listSearchTimer: ReturnType<typeof setTimeout> | undefined

const dialogVisible = ref(false)
const importDialogVisible = ref(false)
const editingUnit = ref<AdministrativeUnitRead | null>(null)

const form = ref<FormState>({
  code: '',
  name: '',
  unit_type: 'ward',
  official_name: '',
  province_code: null,
  is_active: true,
})
const errors = ref<Partial<Record<keyof FormState, string>>>({})

const importForm = ref({
  system_type: 'new' as 'old' | 'new',
  source_name: 'official_import',
  source_version: 'qd19_2025',
  mode: 'merge' as 'merge' | 'replace',
})

const systemOptions = [
  { value: 'new', label: 'Hệ mới (2 cấp)' },
  { value: 'old', label: 'Hệ cũ (3 cấp)' },
]

const activeOptions = [
  { value: null, label: 'Tất cả trạng thái' },
  { value: true, label: 'Đang hoạt động' },
  { value: false, label: 'Đã khóa' },
]

const unitTypeOptions = [
  { value: null, label: 'Tất cả loại đơn vị' },
  { value: 'province', label: 'Tỉnh/Thành phố' },
  { value: 'district', label: 'Quận/Huyện' },
  { value: 'ward', label: 'Xã/Phường' },
]

const creatableUnitTypeOptions = [
  { value: 'province', label: 'Tỉnh/Thành phố' },
  { value: 'district', label: 'Quận/Huyện' },
  { value: 'ward', label: 'Xã/Phường' },
]

const importModeOptions = [
  { value: 'merge', label: 'Merge' },
  { value: 'replace', label: 'Replace' },
]

const provinceOptions = computed(() =>
  provinces.value.map(item => ({
    label: item.name,
    value: item.code,
  })),
)

function typeLabel(type: string) {
  if (type === 'province') return 'Tỉnh/Thành'
  if (type === 'district') return 'Quận/Huyện'
  return 'Xã/Phường'
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

function treeNodeFor(unit: AdministrativeUnitRead): PvTreeNode {
  return {
    key: String(unit.id),
    data: unit,
    children: unit.unit_type === 'province' || unit.unit_type === 'district' ? [] : undefined,
    leaf: unit.unit_type === 'ward',
  }
}

function cacheKeyForProvinces() {
  return `${systemType.value}:${String(filterActive.value)}`
}

async function loadProvinces() {
  const cacheKey = cacheKeyForProvinces()
  const cached = provinceCache.get(cacheKey)
  if (cached) {
    provinces.value = cached
    return
  }

  const res = await administrativeUnitService.listProvinces({
    system_type: systemType.value,
    is_active: filterActive.value,
  })
  provinces.value = res.data
  provinceCache.set(cacheKey, res.data)
}

async function loadList() {
  loadingList.value = true
  try {
    const res = await administrativeUnitService.getList({
      is_active: filterActive.value,
      unit_type: filterUnitType.value,
      province_code: filterProvinceCode.value,
      keyword: listSearchQuery.value.trim() || null,
      page: listPage.value,
      page_size: listPageSize.value,
    })
    units.value = res.data.items
    totalUnits.value = res.data.total
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingList.value = false
  }
}

function loadTreeRoots() {
  treeData.value = provinces.value.map(treeNodeFor)
  expandedKeys.value = {}
}

async function expandTreeNode(node: PvTreeNode) {
  if (node.leaf || node.children === undefined || node.children.length > 0) return

  loadingTree.value = true
  try {
    const res = await administrativeUnitService.listChildren({
      system_type: systemType.value,
      parent_id: Number(node.key),
      is_active: filterActive.value,
    })
    node.children = res.data.map(treeNodeFor)
    node.leaf = node.children.length === 0
    treeData.value = [...treeData.value]
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingTree.value = false
  }
}

function handleNodeExpand(node: unknown) {
  void expandTreeNode(node as PvTreeNode)
}

async function refreshTree() {
  loadingTree.value = true
  try {
    await loadProvinces()
    loadTreeRoots()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 4000 })
  } finally {
    loadingTree.value = false
  }
}

async function refreshView() {
  await Promise.all([refreshTree(), loadList()])
}

function resetListPaging() {
  listPage.value = 1
}

function triggerListSearch() {
  if (listSearchTimer) clearTimeout(listSearchTimer)
  resetListPaging()
  void loadList()
}

function onListSearch() {
  if (listSearchTimer) clearTimeout(listSearchTimer)
  listSearchTimer = setTimeout(() => {
    resetListPaging()
    void loadList()
  }, 300)
}

function onListPage(event: { page?: number; rows?: number }) {
  listPage.value = (event.page ?? 0) + 1
  listPageSize.value = event.rows ?? listPageSize.value
  void loadList()
}

async function handleSystemOrStateChange() {
  provinceCache.clear()
  filterProvinceCode.value = null
  resetListPaging()
  await refreshView()
}

function openCreate() {
  editingUnit.value = null
  form.value = {
    code: '',
    name: '',
    unit_type: 'ward',
    official_name: '',
    province_code: null,
    is_active: true,
  }
  errors.value = {}
  dialogVisible.value = true
}

function openEdit(unit: AdministrativeUnitRead) {
  editingUnit.value = unit
  form.value = {
    code: unit.code,
    name: unit.name,
    unit_type: unit.unit_type as 'province' | 'district' | 'ward',
    official_name: unit.official_name ?? '',
    province_code: unit.province_code,
    is_active: unit.is_active,
  }
  errors.value = {}
  dialogVisible.value = true
}

function validateForm() {
  errors.value = {}
  if (!editingUnit.value && !form.value.code.trim()) errors.value.code = 'Mã đơn vị không được để trống'
  if (!form.value.name.trim()) errors.value.name = 'Tên đơn vị không được để trống'
  if (form.value.unit_type !== 'province' && !form.value.province_code) {
    errors.value.province_code = 'Cần chọn tỉnh/thành phố'
  }
  return Object.keys(errors.value).length === 0
}

async function submitForm() {
  if (!validateForm()) return
  submitting.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      unit_type: form.value.unit_type,
      official_name: form.value.official_name.trim() || form.value.name.trim(),
      province_code: form.value.unit_type === 'province' ? null : form.value.province_code,
      is_active: form.value.is_active,
    }

    if (editingUnit.value) {
      await administrativeUnitService.update(editingUnit.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật đơn vị hành chính', life: 3000 })
    } else {
      await administrativeUnitService.create({
        code: form.value.code.trim(),
        ...payload,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo đơn vị hành chính mới', life: 3000 })
    }
    dialogVisible.value = false
    provinceCache.clear()
    await refreshView()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}

function confirmDelete(unit: AdministrativeUnitRead) {
  confirm.require({
    message: `Bạn có chắc chắn muốn khóa đơn vị "${unit.name}"?`,
    header: 'Xác nhận thao tác',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Khóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        const res = await administrativeUnitService.delete(unit.id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: res.data.message, life: 3000 })
        provinceCache.clear()
        await refreshView()
      } catch (e) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
      }
    },
  })
}

async function submitImport() {
  importing.value = true
  try {
    const res = await administrativeUnitService.importData({
      system_type: importForm.value.system_type,
      source_name: importForm.value.source_name.trim(),
      source_version: importForm.value.source_version.trim(),
      mode: importForm.value.mode,
    })
    importDialogVisible.value = false
    toast.add({
      severity: res.data.failed_rows > 0 ? 'warn' : 'success',
      summary: 'Import hoàn tất',
      detail: `Tổng ${res.data.total_rows}, OK ${res.data.success_rows}, lỗi ${res.data.failed_rows}`,
      life: 4500,
    })
    provinceCache.clear()
    filterProvinceCode.value = null
    resetListPaging()
    await refreshView()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    importing.value = false
  }
}

watch([filterUnitType, filterProvinceCode], () => {
  resetListPaging()
  void loadList()
})

onMounted(refreshView)
</script>

<style scoped>
.page-shell { display: flex; flex-direction: column; gap: 1rem; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}
.page-header h2 { margin: 0; font-size: 1.6rem; font-weight: 700; }
.subtitle { color: var(--p-text-muted-color); }
.header-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.toolbar {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 180px)) minmax(200px, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
}
.toolbar-filter { width: 100%; }
.toolbar-search { width: 100%; }
.content-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.95fr) minmax(420px, 1.25fr);
  gap: 1rem;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1rem 0;
  margin-bottom: 1rem;
}
.card-header h3 { margin: 0; font-size: 1.05rem; font-weight: 700; }
.muted { color: var(--p-text-muted-color); font-size: 0.92rem; }
.tree-name { display: flex; flex-direction: column; gap: 0.2rem; }
.tree-name small { color: var(--p-text-muted-color); }
.action-cell { display: flex; justify-content: flex-end; gap: 0.15rem; }
.form-shell { display: flex; flex-direction: column; gap: 0.85rem; }
.field { display: flex; flex-direction: column; gap: 0.35rem; }
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}
.req { color: #dc2626; }
.error-msg { color: #dc2626; }
.field-switch { gap: 0.6rem; }
.switch-row { display: flex; align-items: center; gap: 0.75rem; }
.active-label { color: #15803d; font-weight: 500; }
.inactive-label { color: #b91c1c; font-weight: 500; }
.hint-box {
  padding: 0.9rem 1rem;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 20%, var(--p-surface-300));
  background: color-mix(in srgb, var(--p-primary-color) 6%, var(--p-surface-0));
  color: var(--p-text-color);
  line-height: 1.5;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem 0;
  color: var(--p-text-muted-color);
}
@media (max-width: 1200px) {
  .content-grid { grid-template-columns: 1fr; }
  .toolbar {
    grid-template-columns: repeat(2, minmax(160px, 1fr));
  }
}
@media (max-width: 768px) {
  .page-header { flex-direction: column; }
  .field-row, .toolbar { grid-template-columns: 1fr; }
}
</style>
