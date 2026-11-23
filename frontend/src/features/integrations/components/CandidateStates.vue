<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Skeleton } from '@/components/ui/skeleton'

/** Loading, failure and "nothing found" for a source's candidates; the list itself is the slot. */
defineProps<{ pending: boolean; error?: string; empty: boolean; rowClass: string }>()
const { t } = useI18n()
</script>

<template>
  <div v-if="pending" class="grid gap-1">
    <Skeleton v-for="i in 4" :key="i" :class="rowClass" class="rounded-md" />
  </div>
  <p v-else-if="error !== undefined" class="text-sm text-destructive" role="alert">
    {{ error }}
  </p>
  <p v-else-if="empty" class="text-sm text-muted-foreground">
    {{ t('integrations.facts.none') }}
  </p>
  <slot v-else />
</template>
