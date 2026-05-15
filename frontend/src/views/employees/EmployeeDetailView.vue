<template>
  <div class="employee-detail-page">
    <div class="page-header">
      <div>
        <h2>Hồ sơ nhân viên</h2>
        <span class="subtitle">Mock integration cho bước chuẩn bị tích hợp địa chỉ hành chính song song</span>
      </div>
    </div>

    <div class="demo-shell">
      <div class="demo-card">
        <div class="demo-intro">
          <span class="eyebrow">Phase 3.1 Preview</span>
          <h3>Thông tin cư trú chuẩn hóa</h3>
          <p>
            Form dưới đây chứng minh contract hiện tại đã đủ để nhập đồng thời địa chỉ hệ cũ
            và hệ mới cho cùng một hồ sơ nhân sự. Chưa có persistence cho employee trong
            phase này.
          </p>
        </div>

        <AdministrativeAddressPairSelector v-model="addressDraft" />
      </div>

      <div class="demo-card">
        <div class="demo-intro">
          <span class="eyebrow">Phase 3.4 Preview</span>
          <h3>Học vấn chuẩn hóa</h3>
          <p>
            Cụm nhập liệu dưới đây chứng minh hồ sơ nhân sự có thể tái sử dụng trực tiếp
            catalog học vấn hiện tại: trình độ, trường học và chuyên ngành. Dữ liệu vẫn là
            draft preview, chưa persistence trong phase này.
          </p>
        </div>

        <div class="education-stack">
          <EmployeeEducationEditor
            v-for="(item, index) in educationDraft"
            :key="item.local_id"
            v-model="educationDraft[index]"
            :index="index"
            @remove="removeEducation(index)"
          />

          <Button
            label="Thêm dòng học vấn"
            icon="pi pi-plus"
            severity="secondary"
            outlined
            @click="addEducation"
          />
        </div>
      </div>

      <div class="preview-card">
        <span class="eyebrow">Payload Preview</span>
        <h3>Dữ liệu sẽ gửi về phase nhân sự</h3>
        <pre>{{ serializedDraft }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'

import AdministrativeAddressPairSelector from '@/components/catalog/AdministrativeAddressPairSelector.vue'
import EmployeeEducationEditor, { type EmployeeEducationDraft } from '@/components/catalog/EmployeeEducationEditor.vue'
import type { AdministrativeAddressSelectionDraft } from '@/services/administrativeUnitService'

interface AddressPairDraft {
  old_address: AdministrativeAddressSelectionDraft
  new_address: AdministrativeAddressSelectionDraft
}

interface EmployeeEducationDraftRow extends EmployeeEducationDraft {
  local_id: string
}

const addressDraft = ref<AddressPairDraft>({
  old_address: {
    system_type: 'old',
    province_unit_id: null,
    district_unit_id: null,
    ward_unit_id: null,
    address_line: '',
  },
  new_address: {
    system_type: 'new',
    province_unit_id: null,
    ward_unit_id: null,
    address_line: '',
  },
})

function makeEducationRow(): EmployeeEducationDraftRow {
  return {
    local_id: crypto.randomUUID(),
    education_level_id: null,
    institution_id: null,
    institution_fallback_text: '',
    major_id: null,
    major_fallback_text: '',
    degree_name: '',
    from_year: null,
    graduation_year: null,
    is_graduated: true,
    note: '',
  }
}

const educationDraft = ref<EmployeeEducationDraftRow[]>([
  makeEducationRow(),
])

function addEducation() {
  educationDraft.value.push(makeEducationRow())
}

function removeEducation(index: number) {
  educationDraft.value.splice(index, 1)
  if (educationDraft.value.length === 0) {
    educationDraft.value.push(makeEducationRow())
  }
}

const serializedDraft = computed(() => JSON.stringify({
  address: addressDraft.value,
  educations: educationDraft.value.map(({ local_id, ...item }) => item),
}, null, 2))
</script>

<style scoped>
.employee-detail-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.page-header {
  margin-bottom: 0.5rem;
}

.page-header h2 {
  margin: 0 0 0.2rem;
  font-size: 1.5rem;
  font-weight: 700;
}

.subtitle,
.demo-intro p {
  color: var(--l-text-muted);
}

.demo-shell {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.9fr);
  gap: 1rem;
}

.demo-card,
.preview-card {
  padding: 1.25rem;
  border-radius: 22px;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.eyebrow {
  display: inline-block;
  margin-bottom: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--p-primary-color) 70%, var(--l-text-muted));
}

.demo-intro h3,
.preview-card h3 {
  margin: 0;
  font-size: 1.15rem;
}

.demo-intro p {
  margin: 0.5rem 0 0;
  line-height: 1.6;
}

.education-stack {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.preview-card pre {
  margin: 1rem 0 0;
  padding: 1rem;
  min-height: 340px;
  overflow: auto;
  border-radius: 16px;
  background: color-mix(in srgb, var(--l-bg) 70%, var(--l-surface));
  color: var(--l-text);
  font-size: 0.85rem;
  line-height: 1.55;
}

@media (max-width: 1200px) {
  .demo-shell {
    grid-template-columns: 1fr;
  }
}
</style>
