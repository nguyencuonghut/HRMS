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
  >
    <template #option="{ option }">
      <div class="option-row">
        <strong>{{ option.name }}</strong>
        <small v-if="option.iso2_code">{{ option.iso2_code }}</small>
      </div>
    </template>
  </AutoComplete>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import otherBusinessCatalogService, { type NationalityRead } from '@/services/otherBusinessCatalogService'

const props = withDefaults(defineProps<{
  modelValue: number | null
  placeholder?: string
}>(), {
  placeholder: 'Chọn quốc tịch...',
})

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const selected = ref<NationalityRead | null>(null)
const suggestions = ref<NationalityRead[]>([])
const loading = ref(false)

async function hydrate() {
  if (!props.modelValue) { selected.value = null; return }
  if (selected.value?.id === props.modelValue) return
  loading.value = true
  try {
    const res = await otherBusinessCatalogService.getNationalityById(props.modelValue)
    selected.value = res.data
  } finally {
    loading.value = false
  }
}

async function search(event: { query: string }) {
  loading.value = true
  try {
    const res = await otherBusinessCatalogService.lookupNationalities({ keyword: event.query.trim() || undefined, limit: 20 })
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

<style scoped>
.option-row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.option-row small {
  color: var(--l-text-muted);
}
</style>
