<template>
  <Dialog
    v-model:visible="visible"
    :header="user ? 'Chỉnh sửa tài khoản' : 'Thêm tài khoản mới'"
    :style="{ width: '480px' }"
    modal
    :close-on-escape="!submitting"
    :closable="!submitting"
    @hide="reset"
  >
    <form class="form" @submit.prevent="submit">
      <div class="field">
        <label>Email <span class="req">*</span></label>
        <InputText
          v-model="form.email"
          class="w-full"
          placeholder="user@company.com"
          :invalid="!!errors.email"
          autocomplete="off"
        />
        <small v-if="errors.email" class="error-msg">{{ errors.email }}</small>
      </div>

      <div class="field">
        <label>Họ và tên <span class="req">*</span></label>
        <InputText
          v-model="form.full_name"
          class="w-full"
          placeholder="Nguyễn Văn A"
          :invalid="!!errors.full_name"
          autocomplete="off"
        />
        <small v-if="errors.full_name" class="error-msg">{{ errors.full_name }}</small>
      </div>

      <template v-if="!user">
        <div class="field">
          <label>Mật khẩu <span class="req">*</span></label>
          <Password
            v-model="form.password"
            class="w-full"
            placeholder="Tối thiểu 8 ký tự, gồm chữ và số"
            :feedback="false"
            toggle-mask
            :input-style="{ width: '100%' }"
            :invalid="!!errors.password"
          />
          <small v-if="errors.password" class="error-msg">{{ errors.password }}</small>
        </div>

        <div class="field">
          <label>Xác nhận mật khẩu <span class="req">*</span></label>
          <Password
            v-model="form.confirm"
            class="w-full"
            placeholder="Nhập lại mật khẩu"
            :feedback="false"
            toggle-mask
            :input-style="{ width: '100%' }"
            :invalid="!!errors.confirm"
          />
          <small v-if="errors.confirm" class="error-msg">{{ errors.confirm }}</small>
        </div>
      </template>

      <div v-if="user" class="field field-switch">
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
      <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="visible = false" />
      <Button
        :label="user ? 'Lưu thay đổi' : 'Tạo mới'"
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
import Password from 'primevue/password'
import ToggleSwitch from 'primevue/toggleswitch'
import userService, { type UserListItem } from '@/services/userService'

const props = defineProps<{ user: UserListItem | null }>()
const emit  = defineEmits<{ (e: 'saved'): void }>()

const visible    = defineModel<boolean>({ required: true })
const toast      = useToast()
const submitting = ref(false)

const form = ref({ email: '', full_name: '', password: '', confirm: '', is_active: true })
const errors = ref<Record<string, string>>({})

watch(visible, (v) => {
  if (v && props.user) {
    form.value = { email: props.user.email, full_name: props.user.full_name,
                   password: '', confirm: '', is_active: props.user.is_active }
  }
})

function reset() {
  form.value = { email: '', full_name: '', password: '', confirm: '', is_active: true }
  errors.value = {}
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.email.trim()) errors.value.email = 'Email không được để trống'
  if (!form.value.full_name.trim()) errors.value.full_name = 'Họ tên không được để trống'
  if (!props.user) {
    if (!form.value.password) {
      errors.value.password = 'Mật khẩu không được để trống'
    } else if (form.value.password.length < 8) {
      errors.value.password = 'Mật khẩu phải có ít nhất 8 ký tự'
    } else if (!/[a-zA-Z]/.test(form.value.password) || !/\d/.test(form.value.password)) {
      errors.value.password = 'Mật khẩu phải có cả chữ và số'
    }
    if (form.value.password !== form.value.confirm) {
      errors.value.confirm = 'Mật khẩu xác nhận không khớp'
    }
  }
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
    if (props.user) {
      await userService.update(props.user.id, {
        email:     form.value.email.trim(),
        full_name: form.value.full_name.trim(),
        is_active: form.value.is_active,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật tài khoản', life: 3000 })
    } else {
      await userService.create({
        email:     form.value.email.trim(),
        full_name: form.value.full_name.trim(),
        password:  form.value.password,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo tài khoản mới', life: 3000 })
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
