<template>
  <nav class="rc-breadcrumb" aria-label="breadcrumb">
    <template v-for="(crumb, i) in crumbs" :key="i">
      <span v-if="i > 0" class="rc-breadcrumb-sep">›</span>
      <RouterLink v-if="crumb.to" :to="crumb.to" class="rc-breadcrumb-link">
        {{ crumb.label }}
      </RouterLink>
      <span v-else class="rc-breadcrumb-current">{{ crumb.label }}</span>
    </template>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  crumbs: Array<{ label: string; to?: string }>
}>()
</script>
