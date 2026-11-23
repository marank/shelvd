<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import WorkPicker from '../components/WorkPicker.vue'
import { backTarget } from '../composables/form'
import { useMergeWork } from '../composables/useMerge'
import { workPage } from '../composables/target'
import { useWork } from '../composables/useWork'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const workId = computed(() => String(route.params.workId))
const work = useWork(workId)
const merge = useMergeWork()
const back = computed(() => backTarget(route.query.back))
const target = ref('')
const error = ref('')
// Start the search with the title minus any edition, e.g. "Dave The Diver".
const initialQuery = computed(() => (work.data.value?.title ?? '').split(/[:\-–(]/)[0]!.trim())

async function submit() {
  error.value = ''
  if (!target.value) {
    error.value = t('works.pickGame')
    return
  }
  try {
    const merged = await merge.mutateAsync({ workId: workId.value, targetId: target.value })
    toast.success(t('works.merged', { title: merged.title }))
    void router.push(workPage(merged.id))
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}
</script>

<template>
  <EditPage
    v-if="work.data.value"
    :title="t('works.mergeGame')"
    :description="t('works.mergeHint')"
    :back="back"
    :busy="merge.isPending.value"
    :save-label="t('works.merge')"
    :error="error"
    @submit="submit"
  >
    <EditSection :title="t('works.thisGame')" :description="t('works.mergeMoves')">
      <div class="grid gap-1 sm:col-span-2" data-testid="merge-source">
        <p class="font-medium">{{ work.data.value.title }}</p>
        <ul class="flex flex-wrap gap-1.5">
          <li
            v-for="release in work.data.value.releases"
            :key="release.id"
            class="flex items-center gap-1"
          >
            <PlatformBadge :platform="release.platform" />
            <span v-if="release.edition" class="text-xs text-muted-foreground">{{
              release.edition
            }}</span>
          </li>
        </ul>
      </div>
    </EditSection>
    <EditSection :title="t('works.mergeInto')" :description="t('works.mergeIntoHint')">
      <div class="sm:col-span-2">
        <WorkPicker v-model="target" :exclude="work.data.value.id" :initial-query="initialQuery" />
      </div>
    </EditSection>
  </EditPage>
</template>
