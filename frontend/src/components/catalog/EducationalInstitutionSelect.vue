<template>
  <div class="catalog-select">
    <AutoComplete
      v-model="selectedInstitution"
      :suggestions="suggestions"
      option-label="name"
      dropdown
      force-selection
      :loading="loading"
      :placeholder="placeholder"
      class="w-full"
      @complete="searchInstitutions"
      @option-select="handleSelect"
      @clear="handleClear"
    >
      <template #option="{ option }">
        <div class="option-row">
          <strong>{{ option.name }}</strong>
          <small>
            {{ option.short_name || option.code || 'Không có tên ngắn' }}
          </small>
        </div>
      </template>
    </AutoComplete>

    <small class="helper-text">
      Nếu chưa có trong catalog, nhập tên trường dự phòng bên dưới.
    </small>

    <InputText
      v-model="fallbackValue"
      class="w-full"
      placeholder="Tên trường dự phòng nếu chưa có trong danh mục"
      @update:modelValue="emitFallback"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import InputText from 'primevue/inputtext'

import educationCatalogService, { type EducationalInstitutionRead } from '@/services/educationCatalogService'

const props = withDefaults(defineProps<{
  modelValue: number | null
  fallbackText?: string
  countryCode?: string | null
  placeholder?: string
}>(), {
  fallbackText: '',
  countryCode: null,
  placeholder: 'Tìm kiếm trường học...',
})

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  'update:fallbackText': [value: string]
}>()

const selectedInstitution = ref<EducationalInstitutionRead | null>(null)
const suggestions = ref<EducationalInstitutionRead[]>([])
const fallbackValue = ref(props.fallbackText)
const loading = ref(false)

async function hydrateSelectedInstitution() {
  if (!props.modelValue) {
    selectedInstitution.value = null
    return
  }

  if (selectedInstitution.value?.id === props.modelValue) return

  loading.value = true
  try {
    const res = await educationCatalogService.getEducationalInstitutionById(props.modelValue)
    selectedInstitution.value = res.data
  } finally {
    loading.value = false
  }
}

async function searchInstitutions(event: { query: string }) {
  loading.value = true
  try {
    const res = await educationCatalogService.lookupEducationalInstitutions({
      keyword: event.query.trim() || null,
      country_code: props.countryCode,
      limit: 20,
    })
    suggestions.value = res.data
  } finally {
    loading.value = false
  }
}

function handleSelect() {
  emit('update:modelValue', selectedInstitution.value?.id ?? null)
  if (selectedInstitution.value) {
    fallbackValue.value = ''
    emit('update:fallbackText', '')
  }
}

function handleClear() {
  selectedInstitution.value = null
  emit('update:modelValue', null)
}

function emitFallback(value: string | undefined) {
  emit('update:fallbackText', value ?? '')
}

watch(() => props.modelValue, () => {
  void hydrateSelectedInstitution()
})

watch(() => props.fallbackText, (value) => {
  fallbackValue.value = value ?? ''
})

onMounted(() => {
  void hydrateSelectedInstitution()
})
</script>

<style scoped>
.catalog-select {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.option-row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.option-row small,
.helper-text {
  color: var(--l-text-muted);
}
</style>
