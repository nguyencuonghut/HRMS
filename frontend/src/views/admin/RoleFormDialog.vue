<template>
  <Dialog
    v-model:visible="visible"
    :header="role ? 'Chỉnh sửa vai trò' : 'Thêm vai trò mới'"
    :style="{ width: '460px' }"
    modal
    :close-on-escape="!submitting"
    :closable="!submitting"
    @hide="reset"
  >
    <form class="form" @submit.prevent="submit">
      <div v-if="!role" class="field">
        <label>Mã vai trò <span class="req">*</span></label>
        <InputText
          v-model="form.code"
          class="w-full"
          placeholder="vd: department_head"
          :invalid="!!errors.code"
          autocomplete="off"
        />
        <small class="field-hint">Chỉ gồm chữ thường, số và dấu gạch dưới</small>
        <small v-if="errors.code" class="error-msg">{{ errors.code }}</small>
      </div>

      <div class="field">
        <label>Tên vai trò <span class="req">*</span></label>
        <InputText
          v-model="form.name"
          class="w-full"
          placeholder="vd: Trưởng phòng"
          :invalid="!!errors.name"
          autocomplete="off"
        />
        <small v-if="errors.name" class="error-msg">{{ errors.name }}</small>
      </div>

      <div class="field">
        <label>Mô tả</label>
        <Textarea
          v-model="form.description"
          class="w-full"
          rows="3"
          placeholder="Mô tả ngắn về vai trò này..."
          auto-resize
        />
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="visible = false" />
      <Button
        :label="role ? 'Lưu thay đổi' : 'Tạo mới'"
        icon="pi pi-check"
        :loading="submitting"
        @click="submit"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import roleService, { type RoleListItem } from '@/services/roleService'

const props = defineProps<{ role: RoleListItem | null }>()
const emit  = defineEmits<{ (e: 'saved'): void }>()

const visible    = defineModel<boolean>({ required: true })
const toast      = useToast()
const submitting = ref(false)

const form   = ref({ code: '', name: '', description: '' })
const errors = ref<Record<string, string>>({})

watch(visible, (v) => {
  if (v && props.role) {
    form.value = { code: props.role.code, name: props.role.name, description: props.role.description ?? '' }
  }
})

function reset() {
  form.value   = { code: '', name: '', description: '' }
  errors.value = {}
}

function validate(): boolean {
  errors.value = {}
  if (!props.role && !form.value.code.trim()) {
    errors.value.code = 'Mã không được để trống'
  } else if (!props.role && !/^[a-z0-9_]+$/.test(form.value.code.trim())) {
    errors.value.code = 'Chỉ gồm chữ thường, số và dấu gạch dưới'
  }
  if (!form.value.name.trim()) errors.value.name = 'Tên không được để trống'
  return Object.keys(errors.value).length === 0
}

function apiError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    if (props.role) {
      await roleService.update(props.role.id, {
        name:        form.value.name.trim(),
        description: form.value.description.trim() || undefined,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật vai trò', life: 3000 })
    } else {
      await roleService.create({
        code:        form.value.code.trim(),
        name:        form.value.name.trim(),
        description: form.value.description.trim() || undefined,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo vai trò mới', life: 3000 })
    }
    visible.value = false
    emit('saved')
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(e), life: 5000 })
  } finally {
    submitting.value = false
  }
}
</script>
