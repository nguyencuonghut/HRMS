<template>
  <AutoComplete
    v-model="internalValue"
    :suggestions="suggestions"
    option-label="name"
    dropdown
    force-selection
    :loading="loading"
    :placeholder="placeholder"
    class="w-full"
    @complete="search"
    @option-select="handleSelect"
    @clear="handleClear"
  >
    <template #option="{ option }">
      <div class="ins-clinic-option">
        <span class="ins-clinic-code">{{ option.code }}</span>
        <span class="ins-clinic-name">{{ option.name }}</span>
      </div>
    </template>
  </AutoComplete>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import bhytClinicService, { type BhytClinicRead } from '@/services/bhytClinicService'

const props = withDefaults(defineProps<{
  modelValue: BhytClinicRead | null
  placeholder?: string
}>(), {
  placeholder: 'Nhập tên hoặc mã bệnh viện...',
})

const emit = defineEmits<{
  'update:modelValue': [value: BhytClinicRead | null]
}>()

const internalValue = ref<BhytClinicRead | null>(props.modelValue)
const suggestions = ref<BhytClinicRead[]>([])
const loading = ref(false)

async function search(event: { query: string }) {
  loading.value = true
  try {
    const res = await bhytClinicService.list({ keyword: event.query || undefined, page: 1, page_size: 20 })
    suggestions.value = res.data.items
  } catch {
    suggestions.value = []
  } finally {
    loading.value = false
  }
}

function handleSelect() {
  emit('update:modelValue', internalValue.value as BhytClinicRead)
}

function handleClear() {
  internalValue.value = null
  emit('update:modelValue', null)
}

watch(() => props.modelValue, (val) => {
  internalValue.value = val
})
</script>
