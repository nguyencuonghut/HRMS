<template>
  <Dialog
    v-model:visible="visible"
    header="Tạo checklist onboarding"
    :modal="true"
    :style="{ width: '480px' }"
    @hide="emit('close')"
  >
    <div class="ob-form">
      <div class="ob-form-field">
        <label class="ob-form-label">Nhân viên <span class="ob-required">*</span></label>
        <Select
          v-model="form.employee_id"
          :options="employees"
          option-label="label"
          option-value="value"
          placeholder="Chọn nhân viên thử việc..."
          :loading="loadingEmps"
          filter
          style="width: 100%"
        />
        <small v-if="errors.employee_id" class="ob-error">{{ errors.employee_id }}</small>
      </div>

      <div class="ob-form-field">
        <label class="ob-form-label">Buddy (tùy chọn)</label>
        <Select
          v-model="form.buddy_user_id"
          :options="users"
          option-label="label"
          option-value="value"
          placeholder="Chọn buddy/mentor..."
          :loading="loadingUsers"
          filter
          show-clear
          style="width: 100%"
        />
      </div>
    </div>

    <template #footer>
      <Button label="Hủy" severity="secondary" outlined @click="emit('close')" />
      <Button label="Tạo checklist" icon="pi pi-check" :loading="saving" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import { onboardingChecklistService } from '@/services/onboardingService'
import api from '@/services/api'

const emit = defineEmits<{
  close: []
  created: []
}>()

const toast = useToast()
const visible = ref(true)

const form = reactive({
  employee_id: null as number | null,
  buddy_user_id: null as number | null,
})
const errors = reactive({ employee_id: '' })

const employees = ref<{ value: number; label: string }[]>([])
const users = ref<{ value: number; label: string }[]>([])
const loadingEmps = ref(false)
const loadingUsers = ref(false)
const saving = ref(false)

onMounted(async () => {
  loadingEmps.value = true
  try {
    // Lấy nhân viên probation chưa có checklist
    const r = await api.get('/employees', { params: { status: 'probation', page_size: 100 } })
    const list = r.data?.items ?? r.data ?? []
    employees.value = list.map((e: { id: number; full_name: string; display_code?: string }) => ({
      value: e.id,
      label: `${e.full_name}${e.display_code ? ` (${e.display_code})` : ''}`,
    }))
  } catch { /* ignore */ }
  finally { loadingEmps.value = false }

  loadingUsers.value = true
  try {
    const r = await api.get('/users', { params: { page_size: 200 } })
    const list = r.data?.items ?? r.data ?? []
    users.value = list.map((u: { id: number; full_name: string }) => ({
      value: u.id,
      label: u.full_name,
    }))
  } catch { /* ignore */ }
  finally { loadingUsers.value = false }
})

async function submit() {
  errors.employee_id = ''
  if (!form.employee_id) {
    errors.employee_id = 'Vui lòng chọn nhân viên'
    return
  }
  saving.value = true
  try {
    await onboardingChecklistService.create({
      employee_id: form.employee_id,
      buddy_user_id: form.buddy_user_id,
    })
    toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo checklist onboarding', life: 3000 })
    emit('created')
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Không thể tạo checklist'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: msg, life: 4000 })
  } finally {
    saving.value = false
  }
}
</script>
