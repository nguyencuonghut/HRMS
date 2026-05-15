<template>
  <section class="education-editor">
    <div class="editor-head">
      <div>
        <span class="editor-kicker">Dòng học vấn {{ index + 1 }}</span>
        <h4>Quá trình học tập chuẩn hóa</h4>
      </div>
      <Button
        icon="pi pi-trash"
        severity="danger"
        text
        rounded
        size="small"
        v-tooltip.top="'Xóa dòng học vấn'"
        @click="$emit('remove')"
      />
    </div>

    <div class="field-grid">
      <div class="field">
        <label>Trình độ học vấn <span class="req">*</span></label>
        <Select
          v-model="draft.education_level_id"
          :options="educationLevelOptions"
          option-label="label"
          option-value="value"
          class="w-full"
          filter
          placeholder="Chọn trình độ học vấn"
        />
      </div>

      <div class="field">
        <label>Tên văn bằng / bằng cấp</label>
        <InputText
          v-model="draft.degree_name"
          class="w-full"
          placeholder="Ví dụ: Kỹ sư Chăn nuôi, Cử nhân Kế toán..."
        />
      </div>
    </div>

    <div class="field-grid">
      <div class="field">
        <label>Trường học</label>
        <EducationalInstitutionSelect
          v-model="draft.institution_id"
          v-model:fallback-text="draft.institution_fallback_text"
        />
      </div>

      <div class="field">
        <label>Chuyên ngành</label>
        <EducationMajorSelect
          v-model="draft.major_id"
          v-model:fallback-text="draft.major_fallback_text"
        />
      </div>
    </div>

    <div class="field-grid field-grid--years">
      <div class="field">
        <label>Năm bắt đầu</label>
        <InputNumber
          v-model="draft.from_year"
          :min="1950"
          :max="2100"
          :max-fraction-digits="0"
          class="w-full"
        />
      </div>

      <div class="field">
        <label>Năm tốt nghiệp</label>
        <InputNumber
          v-model="draft.graduation_year"
          :min="1950"
          :max="2100"
          :max-fraction-digits="0"
          class="w-full"
        />
      </div>

      <div class="field field-switch">
        <label>Đã tốt nghiệp</label>
        <div class="switch-row">
          <ToggleSwitch v-model="draft.is_graduated" />
          <span :class="draft.is_graduated ? 'active-label' : 'inactive-label'">
            {{ draft.is_graduated ? 'Đã hoàn thành' : 'Đang học / chưa hoàn tất' }}
          </span>
        </div>
      </div>
    </div>

    <div class="field">
      <label>Ghi chú</label>
      <Textarea
        v-model="draft.note"
        rows="3"
        class="w-full"
        auto-resize
        placeholder="Ghi chú thêm về quá trình học, chứng chỉ, xếp loại..."
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

import EducationMajorSelect from '@/components/catalog/EducationMajorSelect.vue'
import EducationalInstitutionSelect from '@/components/catalog/EducationalInstitutionSelect.vue'
import educationCatalogService, { type EducationLevelRead } from '@/services/educationCatalogService'

export interface EmployeeEducationDraft {
  education_level_id: number | null
  institution_id: number | null
  institution_fallback_text: string
  major_id: number | null
  major_fallback_text: string
  degree_name: string
  from_year: number | null
  graduation_year: number | null
  is_graduated: boolean
  note: string
}

const props = defineProps<{
  modelValue: EmployeeEducationDraft
  index: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: EmployeeEducationDraft]
  remove: []
}>()

const draft = ref<EmployeeEducationDraft>({ ...props.modelValue })
const educationLevels = ref<EducationLevelRead[]>([])

const educationLevelOptions = computed(() =>
  educationLevels.value.map((item) => ({
    label: `${item.rank_no}. ${item.name}`,
    value: item.id,
  })),
)

let levelsLoaded = false

async function loadEducationLevels() {
  if (levelsLoaded) return
  const res = await educationCatalogService.lookupEducationLevels({ limit: 100 })
  educationLevels.value = res.data
  levelsLoaded = true
}

watch(
  draft,
  (value) => {
    emit('update:modelValue', { ...value })
  },
  { deep: true },
)

watch(
  () => props.modelValue,
  (value) => {
    draft.value = { ...value }
  },
  { deep: true },
)

onMounted(() => {
  void loadEducationLevels()
})
</script>

<style scoped>
.education-editor {
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  padding: 1rem 1.05rem;
  border-radius: 20px;
  border: 1px solid color-mix(in srgb, var(--l-border) 84%, var(--p-primary-color) 16%);
  background: color-mix(in srgb, var(--l-surface) 92%, var(--l-bg) 8%);
}

.editor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.editor-kicker {
  display: inline-block;
  margin-bottom: 0.25rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--p-primary-color) 70%, var(--l-text-muted));
}

.editor-head h4 {
  margin: 0;
  font-size: 1.05rem;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.9rem;
}

.field-grid--years {
  grid-template-columns: 1fr 1fr minmax(220px, 0.9fr);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field-switch {
  justify-content: flex-end;
}

.switch-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 2.625rem;
}

.req {
  color: #dc2626;
}

.active-label {
  color: #15803d;
  font-weight: 500;
}

.inactive-label {
  color: #b91c1c;
  font-weight: 500;
}

@media (max-width: 960px) {
  .field-grid,
  .field-grid--years {
    grid-template-columns: 1fr;
  }
}
</style>
