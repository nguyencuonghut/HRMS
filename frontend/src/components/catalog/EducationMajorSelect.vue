<template>
  <div class="catalog-select">
    <AutoComplete
      v-model="selectedMajor"
      :suggestions="suggestions"
      option-label="name"
      dropdown
      force-selection
      :loading="loading"
      :placeholder="placeholder"
      class="w-full"
      @complete="searchMajors"
      @option-select="handleSelect"
      @clear="handleClear"
    >
      <template #option="{ option }">
        <div class="option-row">
          <strong>{{ option.name }}</strong>
          <small>{{ option.major_group || option.code || 'Không có nhóm' }}</small>
        </div>
      </template>
    </AutoComplete>

    <small class="helper-text">
      Nếu chưa có trong catalog, nhập tên chuyên ngành dự phòng bên dưới.
    </small>

    <InputText
      v-model="fallbackValue"
      class="w-full"
      placeholder="Tên chuyên ngành dự phòng nếu chưa có trong danh mục"
      @update:modelValue="emitFallback"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import InputText from 'primevue/inputtext'

import educationCatalogService, { type EducationMajorRead } from '@/services/educationCatalogService'

const props = withDefaults(defineProps<{
  modelValue: number | null
  fallbackText?: string
  majorGroup?: string | null
  placeholder?: string
}>(), {
  fallbackText: '',
  majorGroup: null,
  placeholder: 'Tìm kiếm chuyên ngành...',
})

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  'update:fallbackText': [value: string]
}>()

const selectedMajor = ref<EducationMajorRead | null>(null)
const suggestions = ref<EducationMajorRead[]>([])
const fallbackValue = ref(props.fallbackText)
const loading = ref(false)

async function hydrateSelectedMajor() {
  if (!props.modelValue) {
    selectedMajor.value = null
    return
  }

  if (selectedMajor.value?.id === props.modelValue) return

  loading.value = true
  try {
    const res = await educationCatalogService.getEducationMajorById(props.modelValue)
    selectedMajor.value = res.data
  } finally {
    loading.value = false
  }
}

async function searchMajors(event: { query: string }) {
  loading.value = true
  try {
    const res = await educationCatalogService.lookupEducationMajors({
      keyword: event.query.trim() || null,
      major_group: props.majorGroup,
      limit: 20,
    })
    suggestions.value = res.data
  } finally {
    loading.value = false
  }
}

function handleSelect() {
  emit('update:modelValue', selectedMajor.value?.id ?? null)
  if (selectedMajor.value) {
    fallbackValue.value = ''
    emit('update:fallbackText', '')
  }
}

function handleClear() {
  selectedMajor.value = null
  emit('update:modelValue', null)
}

function emitFallback(value: string | undefined) {
  emit('update:fallbackText', value ?? '')
}

watch(() => props.modelValue, () => {
  void hydrateSelectedMajor()
})

watch(() => props.fallbackText, (value) => {
  fallbackValue.value = value ?? ''
})

onMounted(() => {
  void hydrateSelectedMajor()
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
