<template>
  <div class="address-editor">
    <template v-if="!editMode">
      <div v-if="initial" class="address-display">
        <div class="address-text" v-if="initial.full_address_text">{{ initial.full_address_text }}</div>

        <div class="system-block" v-if="hasOldAddress">
          <div class="system-row">
            <span class="label-chip">Hệ cũ</span>
            <span class="unit-path">{{ oldAddressPath }}</span>
          </div>
          <div class="detail-line" v-if="initial.old_address_line">{{ initial.old_address_line }}</div>
        </div>

        <div class="system-block" v-if="hasNewAddress">
          <div class="system-row">
            <span class="label-chip is-new">Hệ mới</span>
            <span class="unit-path">{{ newAddressPath }}</span>
          </div>
          <div class="detail-line" v-if="initial.new_address_line">{{ initial.new_address_line }}</div>
        </div>

        <div v-if="!initial.full_address_text && !hasOldAddress && !hasNewAddress" class="empty-address">
          <i class="pi pi-map-marker" />
          <span>Chưa có địa chỉ</span>
        </div>
      </div>
      <div v-else class="empty-address">
        <i class="pi pi-map-marker" />
        <span>Chưa có địa chỉ</span>
      </div>
      <Button
        v-if="!disabled"
        :label="initial ? 'Chỉnh sửa địa chỉ' : 'Thêm địa chỉ'"
        :icon="initial ? 'pi pi-pencil' : 'pi pi-plus'"
        severity="secondary"
        outlined
        size="small"
        class="edit-btn"
        @click="startEdit"
      />
    </template>

    <template v-else>
      <div class="pair-grid">
        <!-- Hệ cũ: 3 cấp -->
        <section class="system-card">
          <div class="system-head">
            <div>
              <span class="system-kicker">Hệ cũ</span>
              <h4>Tỉnh/Thành → Quận/Huyện → Xã/Phường</h4>
            </div>
            <Tag value="3 cấp" severity="contrast" rounded />
          </div>

          <div class="field-grid">
            <div class="field">
              <label>Tỉnh/Thành phố</label>
              <Select
                v-model="form.old_province_unit_id"
                :options="oldProvinces"
                option-label="name"
                option-value="id"
                class="w-full"
                filter
                placeholder="Chọn tỉnh/thành"
                @update:modelValue="onOldProvinceChange"
              />
            </div>
            <div class="field">
              <label>Quận/Huyện</label>
              <Select
                v-model="form.old_district_unit_id"
                :options="oldDistricts"
                option-label="name"
                option-value="id"
                class="w-full"
                filter
                placeholder="Chọn quận/huyện"
                :disabled="!form.old_province_unit_id || loadingOldDistricts"
                @update:modelValue="onOldDistrictChange"
              />
            </div>
            <div class="field">
              <label>Xã/Phường</label>
              <Select
                v-model="form.old_ward_unit_id"
                :options="oldWards"
                option-label="name"
                option-value="id"
                class="w-full"
                filter
                placeholder="Chọn xã/phường"
                :disabled="!form.old_district_unit_id || loadingOldWards"
              />
            </div>
          </div>

          <div class="field">
            <label>Địa chỉ chi tiết hệ cũ</label>
            <InputText v-model="form.old_address_line" class="w-full" placeholder="Số nhà, thôn/xóm, tổ dân phố..." />
          </div>
        </section>

        <!-- Hệ mới: 2 cấp -->
        <section class="system-card">
          <div class="system-head">
            <div>
              <span class="system-kicker">Hệ mới</span>
              <h4>Tỉnh/Thành → Xã/Phường</h4>
            </div>
            <Tag value="2 cấp" severity="info" rounded />
          </div>

          <div class="field-grid field-grid--new">
            <div class="field">
              <label>Tỉnh/Thành phố</label>
              <Select
                v-model="form.new_province_unit_id"
                :options="newProvinces"
                option-label="name"
                option-value="id"
                class="w-full"
                filter
                placeholder="Chọn tỉnh/thành"
                @update:modelValue="onNewProvinceChange"
              />
            </div>
            <div class="field">
              <label>Xã/Phường</label>
              <Select
                v-model="form.new_ward_unit_id"
                :options="newWards"
                option-label="name"
                option-value="id"
                class="w-full"
                filter
                placeholder="Chọn xã/phường"
                :disabled="!form.new_province_unit_id || loadingNewWards"
              />
            </div>
          </div>

          <div class="field">
            <label>Địa chỉ chi tiết hệ mới</label>
            <InputText v-model="form.new_address_line" class="w-full" placeholder="Số nhà, thôn/xóm, tổ dân phố..." />
          </div>
        </section>
      </div>

      <div class="field">
        <label>Địa chỉ đầy đủ (hiển thị)</label>
        <Textarea
          v-model="form.full_address_text"
          class="w-full"
          rows="2"
          placeholder="Ví dụ: 123 Đường Nguyễn Văn A, Phường X, Quận Y, TP. Hồ Chí Minh"
        />
      </div>

      <div class="form-actions">
        <Button label="Hủy" severity="secondary" outlined size="small" :disabled="saving" @click="cancelEdit" />
        <Button label="Lưu địa chỉ" icon="pi pi-check" size="small" :loading="saving" @click="save" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import administrativeUnitService, { type AdministrativeUnitRead } from '@/services/administrativeUnitService'
import employeeService, { type EmployeeAddressRead, type AddressType } from '@/services/employeeService'

const props = defineProps<{
  employeeId: number
  addressType: AddressType
  initial: EmployeeAddressRead | null
  disabled?: boolean
}>()

const emit = defineEmits<{ saved: [] }>()

const toast    = useToast()
const editMode = ref(false)
const saving   = ref(false)

const hasOldAddress = computed(() =>
  !!(props.initial?.old_province_unit_id || props.initial?.old_address_line),
)
const hasNewAddress = computed(() =>
  !!(props.initial?.new_province_unit_id || props.initial?.new_address_line),
)

const oldAddressPath = computed(() => {
  if (!props.initial) return ''
  return [props.initial.old_province_name, props.initial.old_district_name, props.initial.old_ward_name]
    .filter(Boolean).join(' › ')
})

const newAddressPath = computed(() => {
  if (!props.initial) return ''
  return [props.initial.new_province_name, props.initial.new_ward_name]
    .filter(Boolean).join(' › ')
})

const oldProvinces = ref<AdministrativeUnitRead[]>([])
const newProvinces = ref<AdministrativeUnitRead[]>([])
const oldDistricts = ref<AdministrativeUnitRead[]>([])
const oldWards     = ref<AdministrativeUnitRead[]>([])
const newWards     = ref<AdministrativeUnitRead[]>([])

const loadingOldDistricts = ref(false)
const loadingOldWards     = ref(false)
const loadingNewWards     = ref(false)

const form = ref({
  old_province_unit_id: null as number | null,
  old_district_unit_id: null as number | null,
  old_ward_unit_id:     null as number | null,
  old_address_line:     '',
  new_province_unit_id: null as number | null,
  new_ward_unit_id:     null as number | null,
  new_address_line:     '',
  full_address_text:    '',
})

async function loadProvinces() {
  const [oldRes, newRes] = await Promise.all([
    administrativeUnitService.listProvinces({ system_type: 'old', is_active: true }),
    administrativeUnitService.listProvinces({ system_type: 'new', is_active: true }),
  ])
  oldProvinces.value = oldRes.data
  newProvinces.value = newRes.data
}

async function hydrateFromInitial() {
  const src = props.initial
  if (!src) return

  const tasks: Promise<void>[] = []

  if (src.old_province_unit_id) {
    tasks.push((async () => {
      loadingOldDistricts.value = true
      try {
        oldDistricts.value = (await administrativeUnitService.listChildren({ system_type: 'old', parent_id: src.old_province_unit_id!, is_active: true })).data
      } finally { loadingOldDistricts.value = false }
    })())
  }

  if (src.old_district_unit_id) {
    tasks.push((async () => {
      loadingOldWards.value = true
      try {
        oldWards.value = (await administrativeUnitService.listChildren({ system_type: 'old', parent_id: src.old_district_unit_id!, is_active: true })).data
      } finally { loadingOldWards.value = false }
    })())
  }

  if (src.new_province_unit_id) {
    tasks.push((async () => {
      loadingNewWards.value = true
      try {
        newWards.value = (await administrativeUnitService.listChildren({ system_type: 'new', parent_id: src.new_province_unit_id!, is_active: true })).data
      } finally { loadingNewWards.value = false }
    })())
  }

  await Promise.all(tasks)
}

async function startEdit() {
  const src = props.initial
  form.value = {
    old_province_unit_id: src?.old_province_unit_id ?? null,
    old_district_unit_id: src?.old_district_unit_id ?? null,
    old_ward_unit_id:     src?.old_ward_unit_id     ?? null,
    old_address_line:     src?.old_address_line      ?? '',
    new_province_unit_id: src?.new_province_unit_id ?? null,
    new_ward_unit_id:     src?.new_ward_unit_id     ?? null,
    new_address_line:     src?.new_address_line      ?? '',
    full_address_text:    src?.full_address_text      ?? '',
  }
  if (!oldProvinces.value.length) await loadProvinces()
  await hydrateFromInitial()
  editMode.value = true
}

function cancelEdit() { editMode.value = false }

async function onOldProvinceChange() {
  form.value.old_district_unit_id = null
  form.value.old_ward_unit_id     = null
  oldDistricts.value = []
  oldWards.value     = []
  if (!form.value.old_province_unit_id) return
  loadingOldDistricts.value = true
  try {
    oldDistricts.value = (await administrativeUnitService.listChildren({ system_type: 'old', parent_id: form.value.old_province_unit_id, is_active: true })).data
  } finally { loadingOldDistricts.value = false }
}

async function onOldDistrictChange() {
  form.value.old_ward_unit_id = null
  oldWards.value = []
  if (!form.value.old_district_unit_id) return
  loadingOldWards.value = true
  try {
    oldWards.value = (await administrativeUnitService.listChildren({ system_type: 'old', parent_id: form.value.old_district_unit_id, is_active: true })).data
  } finally { loadingOldWards.value = false }
}

async function onNewProvinceChange() {
  form.value.new_ward_unit_id = null
  newWards.value = []
  if (!form.value.new_province_unit_id) return
  loadingNewWards.value = true
  try {
    newWards.value = (await administrativeUnitService.listChildren({ system_type: 'new', parent_id: form.value.new_province_unit_id, is_active: true })).data
  } finally { loadingNewWards.value = false }
}

async function save() {
  saving.value = true
  try {
    await employeeService.upsertAddress(props.employeeId, {
      address_type:         props.addressType,
      old_province_unit_id: form.value.old_province_unit_id,
      old_district_unit_id: form.value.old_district_unit_id,
      old_ward_unit_id:     form.value.old_ward_unit_id,
      old_address_line:     form.value.old_address_line.trim() || null,
      new_province_unit_id: form.value.new_province_unit_id,
      new_ward_unit_id:     form.value.new_ward_unit_id,
      new_address_line:     form.value.new_address_line.trim() || null,
      full_address_text:    form.value.full_address_text.trim() || null,
    })
    toast.add({ severity: 'success', summary: 'Đã lưu', detail: 'Địa chỉ đã được cập nhật', life: 3000 })
    editMode.value = false
    emit('saved')
  } catch (e) {
    const err = e as { response?: { data?: { detail?: string } } }
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err.response?.data?.detail ?? 'Đã xảy ra lỗi', life: 4000 })
  } finally {
    saving.value = false
  }
}

watch(() => props.initial, () => { editMode.value = false })
</script>

<style scoped>
/* ── View mode ─────────────────────────────────────────────────────────────── */
.address-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.address-display {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.address-text { font-size: 0.9rem; line-height: 1.5; }

.system-block { display: flex; flex-direction: column; gap: 0.2rem; }

.system-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
}

.unit-path { color: var(--l-text-muted); }

.detail-line {
  font-size: 0.8rem;
  color: var(--l-text-muted);
  padding-left: 2.2rem;
}

.empty-address {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--l-text-muted);
  font-size: 0.875rem;
}

.edit-btn { align-self: flex-start; }

/* ── Edit mode ─────────────────────────────────────────────────────────────── */
.pair-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.system-card {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem;
  border-radius: 16px;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
}

.system-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
}

.system-kicker {
  display: inline-block;
  margin-bottom: 0.25rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--p-primary-color) 70%, var(--l-text-muted));
}

.system-head h4 { margin: 0; font-size: 0.95rem; font-weight: 600; }

.field-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.6rem;
}

.field-grid--new { grid-template-columns: repeat(2, minmax(0, 1fr)); }

/* Cancel global field margin-bottom inside grids */
.field-grid .field,
.field-grid--new .field { margin-bottom: 0; }

@media (max-width: 1100px) {
  .pair-grid,
  .field-grid,
  .field-grid--new { grid-template-columns: 1fr; }
}
</style>
