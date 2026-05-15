<template>
  <AutoComplete
    v-model="selected"
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
  />
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import otherBusinessCatalogService, { type EthnicityRead } from '@/services/otherBusinessCatalogService'

const props = withDefaults(defineProps<{
  modelValue: number | null
  placeholder?: string
}>(), {
  placeholder: 'Chọn dân tộc...',
})

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const selected = ref<EthnicityRead | null>(null)
const suggestions = ref<EthnicityRead[]>([])
const loading = ref(false)

async function hydrate() {
  if (!props.modelValue) { selected.value = null; return }
  if (selected.value?.id === props.modelValue) return
  loading.value = true
  try {
    const res = await otherBusinessCatalogService.getEthnicityById(props.modelValue)
    selected.value = res.data
  } finally {
    loading.value = false
  }
}

async function search(event: { query: string }) {
  loading.value = true
  try {
    const res = await otherBusinessCatalogService.lookupEthnicities({ keyword: event.query.trim() || undefined, limit: 30 })
    suggestions.value = res.data
  } finally {
    loading.value = false
  }
}

function handleSelect() { emit('update:modelValue', selected.value?.id ?? null) }
function handleClear() { selected.value = null; emit('update:modelValue', null) }

watch(() => props.modelValue, () => void hydrate())
onMounted(() => void hydrate())
</script>
