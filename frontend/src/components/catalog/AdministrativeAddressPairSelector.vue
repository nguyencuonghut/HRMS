<template>
  <div class="address-pair-selector">
    <div class="pair-header">
      <div>
        <h3>Địa chỉ hành chính song song</h3>
        <p>
          Hồ sơ nhân sự sẽ lưu đồng thời cả địa chỉ theo hệ cũ và hệ mới. Hai cụm chọn
          dưới đây dùng chung catalog hiện tại.
        </p>
      </div>
      <Button
        label="Kiểm tra cả hai hệ"
        icon="pi pi-check-circle"
        severity="secondary"
        outlined
        :loading="validating"
        @click="validateBoth"
      />
    </div>

    <div class="pair-grid">
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
              v-model="draft.old_address.province_unit_id"
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
              v-model="draft.old_address.district_unit_id"
              :options="oldDistricts"
              option-label="name"
              option-value="id"
              class="w-full"
              filter
              placeholder="Chọn quận/huyện"
              :disabled="!draft.old_address.province_unit_id || loadingOldDistricts"
              @update:modelValue="onOldDistrictChange"
            />
          </div>

          <div class="field">
            <label>Xã/Phường</label>
            <Select
              v-model="draft.old_address.ward_unit_id"
              :options="oldWards"
              option-label="name"
              option-value="id"
              class="w-full"
              filter
              placeholder="Chọn xã/phường"
              :disabled="!draft.old_address.district_unit_id || loadingOldWards"
            />
          </div>
        </div>

        <div class="field">
          <label>Địa chỉ chi tiết hệ cũ</label>
          <InputText
            v-model="draft.old_address.address_line"
            class="w-full"
            placeholder="Số nhà, thôn/xóm, tổ dân phố..."
          />
        </div>

        <Message v-if="validationResult" :severity="validationResult.old_address.valid ? 'success' : 'warn'" :closable="false">
          {{ validationResult.old_address.message }}
        </Message>
      </section>

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
              v-model="draft.new_address.province_unit_id"
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
              v-model="draft.new_address.ward_unit_id"
              :options="newWards"
              option-label="name"
              option-value="id"
              class="w-full"
              filter
              placeholder="Chọn xã/phường"
              :disabled="!draft.new_address.province_unit_id || loadingNewWards"
            />
          </div>
        </div>

        <div class="field">
          <label>Địa chỉ chi tiết hệ mới</label>
          <InputText
            v-model="draft.new_address.address_line"
            class="w-full"
            placeholder="Số nhà, thôn/xóm, tổ dân phố..."
          />
        </div>

        <Message v-if="validationResult" :severity="validationResult.new_address.valid ? 'success' : 'warn'" :closable="false">
          {{ validationResult.new_address.message }}
        </Message>
      </section>
    </div>

    <Message v-if="validationResult" :severity="validationResult.valid ? 'success' : 'warn'" :closable="false">
      {{ validationResult.message }}
    </Message>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import administrativeUnitService, {
  type AdministrativeAddressSelectionDraft,
  type AdministrativeUnitRead,
  type ValidateDualLocationPathsResult,
} from '@/services/administrativeUnitService'

interface AddressPairModel {
  old_address: AdministrativeAddressSelectionDraft
  new_address: AdministrativeAddressSelectionDraft
}

const props = defineProps<{
  modelValue: AddressPairModel
}>()

const emit = defineEmits<{
  'update:modelValue': [value: AddressPairModel]
}>()

const oldProvinces = ref<AdministrativeUnitRead[]>([])
const newProvinces = ref<AdministrativeUnitRead[]>([])
const oldDistricts = ref<AdministrativeUnitRead[]>([])
const oldWards = ref<AdministrativeUnitRead[]>([])
const newWards = ref<AdministrativeUnitRead[]>([])

const loadingOldDistricts = ref(false)
const loadingOldWards = ref(false)
const loadingNewWards = ref(false)
const validating = ref(false)
const validationResult = ref<ValidateDualLocationPathsResult | null>(null)

function cloneDraft(value: AddressPairModel): AddressPairModel {
  return {
    old_address: {
      ...value.old_address,
    },
    new_address: {
      ...value.new_address,
    },
  }
}

const draft = ref<AddressPairModel>(cloneDraft(props.modelValue))

async function loadProvinces() {
  const [oldRes, newRes] = await Promise.all([
    administrativeUnitService.listProvinces({ system_type: 'old', is_active: true }),
    administrativeUnitService.listProvinces({ system_type: 'new', is_active: true }),
  ])
  oldProvinces.value = oldRes.data
  newProvinces.value = newRes.data
  await hydrateExistingSelections()
}

async function onOldProvinceChange() {
  draft.value.old_address.district_unit_id = null
  draft.value.old_address.ward_unit_id = null
  oldDistricts.value = []
  oldWards.value = []
  validationResult.value = null

  if (!draft.value.old_address.province_unit_id) return
  loadingOldDistricts.value = true
  try {
    const res = await administrativeUnitService.listChildren({
      system_type: 'old',
      parent_id: draft.value.old_address.province_unit_id,
      is_active: true,
    })
    oldDistricts.value = res.data
  } finally {
    loadingOldDistricts.value = false
  }
}

async function onOldDistrictChange() {
  draft.value.old_address.ward_unit_id = null
  oldWards.value = []
  validationResult.value = null

  if (!draft.value.old_address.district_unit_id) return
  loadingOldWards.value = true
  try {
    const res = await administrativeUnitService.listChildren({
      system_type: 'old',
      parent_id: draft.value.old_address.district_unit_id,
      is_active: true,
    })
    oldWards.value = res.data
  } finally {
    loadingOldWards.value = false
  }
}

async function onNewProvinceChange() {
  draft.value.new_address.ward_unit_id = null
  newWards.value = []
  validationResult.value = null

  if (!draft.value.new_address.province_unit_id) return
  loadingNewWards.value = true
  try {
    const res = await administrativeUnitService.listChildren({
      system_type: 'new',
      parent_id: draft.value.new_address.province_unit_id,
      is_active: true,
    })
    newWards.value = res.data
  } finally {
    loadingNewWards.value = false
  }
}

async function validateBoth() {
  if (
    !draft.value.old_address.province_unit_id ||
    !draft.value.old_address.district_unit_id ||
    !draft.value.old_address.ward_unit_id ||
    !draft.value.new_address.province_unit_id ||
    !draft.value.new_address.ward_unit_id
  ) {
    validationResult.value = {
      valid: false,
      message: 'Cần chọn đủ cả địa chỉ hệ cũ và hệ mới trước khi kiểm tra.',
      old_address: { valid: false, message: 'Thiếu thông tin địa chỉ hệ cũ' },
      new_address: { valid: false, message: 'Thiếu thông tin địa chỉ hệ mới' },
    }
    return
  }

  validating.value = true
  try {
    const res = await administrativeUnitService.validateDualLocationPaths({
      old_address: {
        system_type: 'old',
        province_unit_id: draft.value.old_address.province_unit_id,
        district_unit_id: draft.value.old_address.district_unit_id,
        ward_unit_id: draft.value.old_address.ward_unit_id,
        address_line: draft.value.old_address.address_line ?? null,
      },
      new_address: {
        system_type: 'new',
        province_unit_id: draft.value.new_address.province_unit_id,
        ward_unit_id: draft.value.new_address.ward_unit_id,
        address_line: draft.value.new_address.address_line ?? null,
      },
    })
    validationResult.value = res.data
  } finally {
    validating.value = false
  }
}

async function hydrateExistingSelections() {
  if (draft.value.old_address.province_unit_id) {
    loadingOldDistricts.value = true
    try {
      const res = await administrativeUnitService.listChildren({
        system_type: 'old',
        parent_id: draft.value.old_address.province_unit_id,
        is_active: true,
      })
      oldDistricts.value = res.data
    } finally {
      loadingOldDistricts.value = false
    }
  }

  if (draft.value.old_address.district_unit_id) {
    loadingOldWards.value = true
    try {
      const res = await administrativeUnitService.listChildren({
        system_type: 'old',
        parent_id: draft.value.old_address.district_unit_id,
        is_active: true,
      })
      oldWards.value = res.data
    } finally {
      loadingOldWards.value = false
    }
  }

  if (draft.value.new_address.province_unit_id) {
    loadingNewWards.value = true
    try {
      const res = await administrativeUnitService.listChildren({
        system_type: 'new',
        parent_id: draft.value.new_address.province_unit_id,
        is_active: true,
      })
      newWards.value = res.data
    } finally {
      loadingNewWards.value = false
    }
  }
}

watch(
  () => props.modelValue,
  (value) => {
    draft.value = cloneDraft(value)
    validationResult.value = null
  },
  { deep: true },
)

watch(
  draft,
  (value) => {
    emit('update:modelValue', cloneDraft(value))
  },
  { deep: true },
)

onMounted(loadProvinces)
</script>

<style scoped>
.address-pair-selector {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pair-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.pair-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.pair-header p {
  margin: 0.35rem 0 0;
  color: var(--l-text-muted);
  line-height: 1.6;
}

.pair-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.system-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.1rem;
  border-radius: 20px;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.system-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.system-kicker {
  display: inline-block;
  margin-bottom: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--p-primary-color) 70%, var(--l-text-muted));
}

.system-head h4 {
  margin: 0;
  font-size: 1rem;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.field-grid--new {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.field label {
  font-size: 0.88rem;
  font-weight: 600;
}

@media (max-width: 1100px) {
  .pair-grid,
  .field-grid,
  .field-grid--new {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .pair-header {
    flex-direction: column;
  }
}
</style>
