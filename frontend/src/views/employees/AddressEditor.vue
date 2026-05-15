<template>
  <div class="address-editor">
    <template v-if="!editMode">
      <div v-if="initial" class="address-display">
        <div class="address-text">{{ initial.full_address_text || '(chưa có địa chỉ đầy đủ)' }}</div>
        <div class="address-meta" v-if="initial.old_address_line">
          <span class="label-chip">Hệ cũ</span> {{ initial.old_address_line }}
        </div>
        <div class="address-meta" v-if="initial.new_address_line">
          <span class="label-chip">Hệ mới</span> {{ initial.new_address_line }}
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
      <div class="form-grid">
        <div class="field col-full">
          <label>Địa chỉ đầy đủ (hiển thị)</label>
          <Textarea
            v-model="form.full_address_text"
            class="w-full"
            rows="2"
            placeholder="Ví dụ: 123 Đường Nguyễn Văn A, Phường X, Quận Y, TP. Hồ Chí Minh"
          />
        </div>
        <div class="field">
          <label>Số nhà, đường (hệ cũ)</label>
          <InputText v-model="form.old_address_line" class="w-full" placeholder="123 Đường ABC" />
        </div>
        <div class="field">
          <label>Số nhà, đường (hệ mới)</label>
          <InputText v-model="form.new_address_line" class="w-full" placeholder="123 Đường ABC" />
        </div>
      </div>
      <div class="form-actions">
        <Button label="Hủy" severity="secondary" outlined size="small" :disabled="saving" @click="cancelEdit" />
        <Button label="Lưu địa chỉ" icon="pi pi-check" size="small" :loading="saving" @click="save" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
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

const form = ref({
  full_address_text: '',
  old_address_line: '',
  new_address_line: '',
})

function startEdit() {
  form.value = {
    full_address_text: props.initial?.full_address_text ?? '',
    old_address_line: props.initial?.old_address_line ?? '',
    new_address_line: props.initial?.new_address_line ?? '',
  }
  editMode.value = true
}

function cancelEdit() { editMode.value = false }

async function save() {
  saving.value = true
  try {
    await employeeService.upsertAddress(props.employeeId, {
      address_type: props.addressType,
      old_address_line: form.value.old_address_line.trim() || null,
      new_address_line: form.value.new_address_line.trim() || null,
      full_address_text: form.value.full_address_text.trim() || null,
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

.address-text {
  font-size: 0.9rem;
  line-height: 1.5;
}

.address-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: var(--l-text-muted);
}

.label-chip {
  display: inline-block;
  padding: 0.05rem 0.4rem;
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 700;
}

.empty-address {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--l-text-muted);
  font-size: 0.875rem;
}

.edit-btn { align-self: flex-start; }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field label {
  font-size: 0.85rem;
  font-weight: 500;
}

.col-full { grid-column: 1 / -1; }

.form-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

@media (max-width: 600px) {
  .form-grid { grid-template-columns: 1fr; }
  .col-full { grid-column: 1; }
}
</style>
