<script setup lang="ts">
import { CopyCheck } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Release } from '@/api/types'
import { useOwned } from '@/features/library/composables/useOwned'
import { useUiStore } from '@/stores/ui'

/** "Schon 1× in der Bibliothek": keeps a second copy from slipping in unnoticed. */
const props = defineProps<{ release: Release }>()
const { t } = useI18n()
const ui = useUiStore()
const owned = useOwned(() => ui.addLibraryId ?? '')
const copies = computed(() => owned.data.value?.releases.get(props.release.id) ?? 0)
const ofGame = computed(() => owned.data.value?.works.get(props.release.work_id) ?? 0)
</script>

<template>
  <span
    v-if="copies || ofGame"
    class="flex items-center gap-1 text-xs font-medium text-warning"
    data-testid="owned-hint"
  >
    <CopyCheck class="size-3.5 shrink-0" />
    {{ copies ? t('add.owned.release', { n: copies }) : t('add.owned.game', { n: ofGame }) }}
  </span>
</template>
