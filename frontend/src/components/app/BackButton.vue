<script setup lang="ts">
import { ArrowLeft } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useRouter, type RouteLocationRaw } from 'vue-router'

/** "Back" on detail pages: where you came from, else `fallback` (default: the library's
 * explorer). */
const props = defineProps<{ libraryId?: string; fallback?: RouteLocationRaw }>()
const { t } = useI18n()
const router = useRouter()

function back() {
  if (window.history.state?.back) router.back()
  else
    void router.push(props.fallback ?? { name: 'explorer', params: { libraryId: props.libraryId } })
}
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
    @click="back"
  >
    <ArrowLeft class="size-3.5" /> {{ t('actions.back') }}
  </button>
</template>
