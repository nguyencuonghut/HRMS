<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Sinh hợp đồng từ mẫu"
    style="width: 480px;"
  >
    <div class="field">
      <div class="generate-contract-info">
        <i class="pi pi-file-edit" />
        <span>Hợp đồng: <strong>{{ props.contract?.contract_number }}</strong></span>
      </div>
    </div>

    <div class="field">
      <label class="field-label">Chọn mẫu hợp đồng <span class="req">*</span></label>
      <Select
        v-model="selectedTemplateId"
        :options="templateOptions"
        option-label="label"
        option-value="value"
        placeholder="— Chọn mẫu —"
        filter
        :filter-placeholder="'Tìm mẫu...'"
        fluid
        :loading="loadingTemplates"
        :empty-message="loadingTemplates ? 'Đang tải...' : 'Không có mẫu nào phù hợp'"
      />
      <small v-if="templateOptions.length === 0 && !loadingTemplates" class="p-error">
        Chưa có mẫu nào có file DOCX cho loại hợp đồng này.
      </small>
    </div>

    <div class="generate-hint">
      <i class="pi pi-info-circle" />
      File Word (.docx) sẽ được tải về máy với dữ liệu nhân viên đã điền sẵn.
    </div>

    <template #footer>
      <Button label="Hủy" text @click="visible = false" />
      <Button
        label="Tải về Word"
        icon="pi pi-download"
        :loading="generating"
        :disabled="!selectedTemplateId"
        @click="doGenerate"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'

import contractService, { type ContractRead } from '@/services/contractService'
import otherBusinessCatalogService from '@/services/otherBusinessCatalogService'

const props = defineProps<{
  employeeId: number
  contract: ContractRead | null
}>()

const visible = defineModel<boolean>({ required: true })
const toast   = useToast()

const loadingTemplates  = ref(false)
const generating        = ref(false)
const selectedTemplateId = ref<number | null>(null)
const templateOptions   = ref<{ label: string; value: number }[]>([])

watch(visible, async (val) => {
  if (!val || !props.contract) return
  selectedTemplateId.value = null
  templateOptions.value = []
  loadingTemplates.value = true
  try {
    const resp = await otherBusinessCatalogService.getContractTemplates({
      document_kind: props.contract.document_kind,
      is_active: true,
      page_size: 200,
    })
    templateOptions.value = resp.data.items
      .filter(t => t.storage_path)
      .map(t => ({ label: `${t.name} (v${t.version_no})`, value: t.id }))
  } catch {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không tải được danh sách mẫu', life: 3000 })
  } finally {
    loadingTemplates.value = false
  }
})

async function doGenerate() {
  if (!selectedTemplateId.value || !props.contract) return
  generating.value = true
  try {
    const filename = `HD_${props.contract.contract_number}.docx`
    await contractService.generateContract(
      props.employeeId,
      props.contract.id,
      selectedTemplateId.value,
      filename,
    )
    toast.add({ severity: 'success', summary: 'Đang tải về', detail: filename, life: 3000 })
    visible.value = false
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    const detail = err.response?.data?.detail
    toast.add({ severity: 'error', summary: 'Lỗi sinh hợp đồng', detail: detail ?? 'Không thể sinh hợp đồng', life: 5000 })
  } finally {
    generating.value = false
  }
}
</script>
