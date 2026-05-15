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
        <strong>{{ option.short_name || option.name }}</strong>
        <small>{{ option.name }}</small>
      </div>
    </template>
  </AutoComplete>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import otherBusinessCatalogService, { type BankRead } from '@/services/otherBusinessCatalogService'

const props = withDefaults(defineProps<{
  modelValue: number | null
  placeholder?: string
}>(), {
  placeholder: 'Tìm kiếm ngân hàng...',
})

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const selected = ref<BankRead | null>(null)
const suggestions = ref<BankRead[]>([])
const loading = ref(false)

async function hydrate() {
  if (!props.modelValue) { selected.value = null; return }
  if (selected.value?.id === props.modelValue) return
  loading.value = true
  try {
    const res = await otherBusinessCatalogService.getBankById(props.modelValue)
    selected.value = res.data
  } finally {
    loading.value = false
  }
}

async function search(event: { query: string }) {
  loading.value = true
  try {
    const res = await otherBusinessCatalogService.lookupBanks({ keyword: event.query.trim() || undefined, limit: 20 })
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
  gap: 0.1rem;
}
.option-row small {
  color: var(--l-text-muted);
  font-size: 0.8rem;
}
</style>
