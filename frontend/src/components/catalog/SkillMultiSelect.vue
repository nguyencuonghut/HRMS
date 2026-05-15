<template>
  <div class="skill-multi-select">
    <AutoComplete
      v-model="inputText"
      :suggestions="suggestions"
      option-label="name"
      :loading="loading"
      placeholder="Tìm kiếm kỹ năng để thêm..."
      class="w-full"
      @complete="search"
      @option-select="handleAdd"
    >
      <template #option="{ option }">
        <div class="option-row">
          <strong>{{ option.name }}</strong>
          <small v-if="option.skill_group">{{ option.skill_group }}</small>
        </div>
      </template>
    </AutoComplete>

    <div v-if="selectedSkills.length" class="tag-list">
      <Tag
        v-for="skill in selectedSkills"
        :key="skill.id"
        :value="skill.name"
        severity="secondary"
        class="skill-tag"
      >
        <template #default>
          {{ skill.name }}
          <button class="remove-btn" @click="handleRemove(skill.id)">×</button>
        </template>
      </Tag>
    </div>
    <small v-else class="empty-hint">Chưa có kỹ năng nào được chọn.</small>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import Tag from 'primevue/tag'
import otherBusinessCatalogService, { type SkillRead } from '@/services/otherBusinessCatalogService'

const props = defineProps<{
  modelValue: number[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

const selectedSkills = ref<SkillRead[]>([])
const suggestions = ref<SkillRead[]>([])
const inputText = ref('')
const loading = ref(false)

const selectedIds = computed(() => new Set(selectedSkills.value.map(s => s.id)))

async function hydrateAll() {
  if (!props.modelValue.length) { selectedSkills.value = []; return }
  const missing = props.modelValue.filter(id => !selectedIds.value.has(id))
  if (!missing.length) return
  loading.value = true
  try {
    const results = await Promise.all(missing.map(id => otherBusinessCatalogService.getSkillById(id)))
    for (const res of results) {
      if (!selectedIds.value.has(res.data.id)) {
        selectedSkills.value.push(res.data)
      }
    }
  } finally {
    loading.value = false
  }
}

async function search(event: { query: string }) {
  loading.value = true
  try {
    const res = await otherBusinessCatalogService.lookupSkills({ keyword: event.query.trim() || undefined, limit: 20 })
    suggestions.value = res.data.filter(s => !selectedIds.value.has(s.id))
  } finally {
    loading.value = false
  }
}

function handleAdd(event: { value: SkillRead }) {
  const skill = event.value
  if (!selectedIds.value.has(skill.id)) {
    selectedSkills.value.push(skill)
    emit('update:modelValue', selectedSkills.value.map(s => s.id))
  }
  inputText.value = ''
}

function handleRemove(id: number) {
  selectedSkills.value = selectedSkills.value.filter(s => s.id !== id)
  emit('update:modelValue', selectedSkills.value.map(s => s.id))
}

watch(() => props.modelValue, () => void hydrateAll(), { deep: true })
onMounted(() => void hydrateAll())
</script>

<style scoped>
.skill-multi-select {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.skill-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0 0.1rem;
  font-size: 1rem;
  line-height: 1;
  color: inherit;
  opacity: 0.7;
}

.remove-btn:hover {
  opacity: 1;
}

.empty-hint,
.option-row small {
  color: var(--l-text-muted);
}

.option-row {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
</style>
