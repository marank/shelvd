<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Label } from '@/components/ui/label'
import TermPicker from '@/features/works/components/TermPicker.vue'
import type { PickedTerm } from '@/features/works/composables/useTerms'
import { termPage } from '@/lib/terms'
import TermWorkCard from '../components/TermWorkCard.vue'
import { termGames, useTerm, useTermMutations } from '../composables/useTermPages'
import { useTermRoute } from '../composables/useTermRoute'

/** Merging duplicates ("Level-5" / "Level 5", typos): every game of this entry gets the
 * picked one instead, then this one is deleted. */
const { t } = useI18n()
const router = useRouter()
const { kind, termId } = useTermRoute()
const term = useTerm(kind, termId)
const { merge } = useTermMutations(kind)
const back = computed(() => termPage(kind.value, termId.value))
const target = ref<PickedTerm[]>([])
const error = ref('')
const games = computed(() => termGames(term.data.value))

async function submit() {
  error.value = ''
  const targetId = target.value[0]?.id
  if (!targetId) {
    error.value = t('terms.pickTarget')
    return
  }
  try {
    const merged = await merge.mutateAsync({ termId: termId.value, targetId })
    toast.success(t('terms.merged', { name: merged.name }))
    void router.replace(termPage(kind.value, merged.id))
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}
</script>

<template>
  <EditPage
    v-if="term.data.value"
    :title="t('terms.mergeTitle', { name: term.data.value.name })"
    :description="t('terms.mergeHint')"
    :back="back"
    :busy="merge.isPending.value"
    :save-label="t('terms.merge')"
    :error="error"
    @submit="submit"
  >
    <EditSection :title="t('terms.mergeInto')" :description="t('terms.mergeIntoHint')">
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="merge-target">{{ t(`terms.${kind}.one`) }}</Label>
        <TermPicker
          id="merge-target"
          v-model="target"
          :kind="kind"
          existing-only
          :exclude="[termId]"
        />
      </div>
    </EditSection>
    <EditSection
      :title="t('terms.moves', { n: games.length }, games.length)"
      :description="t('terms.movesHint')"
    >
      <div class="sm:col-span-2">
        <div
          v-if="games.length"
          class="grid grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] items-end gap-x-2 gap-y-3"
        >
          <TermWorkCard v-for="work in games" :key="work.id" :work="work" />
        </div>
        <p v-else class="text-sm text-muted-foreground">{{ t('terms.unused') }}</p>
      </div>
    </EditSection>
  </EditPage>
</template>
