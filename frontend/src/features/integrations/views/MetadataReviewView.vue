<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import type { components } from '@/api/schema'
import { formatReleaseDate, type Precision } from '@/lib/releaseDate'
import { backTarget } from '@/features/works/composables/form'
import { useProviders } from '@/features/library/composables/useReference'
import { useWork } from '@/features/works/composables/useWork'
import { useApplyMetadata, useMetadataPreview } from '../composables/useFacts'

type Change = components['schemas']['MetadataChangeOut']
type Value = components['schemas']['MetadataValueOut']

/** What a metadata source's entry would change, current against proposed, field by field.
 * Empty fields and more precise dates are ticked; whatever merely differs is not. */
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const workId = computed(() => String(route.params.workId))
const source = computed(() => String(route.params.source))
const externalId = computed(() => String(route.params.externalId))
const work = useWork(workId)
const providers = useProviders()
const label = computed(
  () => providers.data.value?.find((p) => p.name === source.value)?.label ?? source.value,
)
const back = computed(() => backTarget(route.query.back))
const preview = useMetadataPreview(workId, source, externalId)
const apply = useApplyMetadata()

const chosen = ref(new Set<string>())
watch(
  () => preview.data.value,
  (data) => (chosen.value = new Set(data?.changes.filter((c) => c.suggested).map((c) => c.id))),
  { immediate: true },
)
function toggle(id: string, on: boolean | 'indeterminate') {
  const next = new Set(chosen.value)
  if (on === true) next.add(id)
  else next.delete(id)
  chosen.value = next
}

/** The game's changes first, then one block per release, in the preview's order. */
const groups = computed(() => {
  const result: { key: string; title: string; changes: Change[] }[] = []
  for (const change of preview.data.value?.changes ?? []) {
    const key = change.release_id ?? 'work'
    let group = result.find((g) => g.key === key)
    if (!group) {
      group = { key, title: groupTitle(change.release_id), changes: [] }
      result.push(group)
    }
    group.changes.push(change)
  }
  return result
})
function groupTitle(releaseId: string | null) {
  if (!releaseId) return t('levels.work')
  const release = work.data.value?.releases.find((r) => r.id === releaseId)
  if (!release) return t('levels.release')
  const parts = [
    release.platform.short_name || release.platform.name,
    t(`choices.region.${release.region}`),
    release.edition,
  ]
  return `${t('levels.release')} · ${parts.filter(Boolean).join(' · ')}`
}

const dateText = (value: Value) =>
  value.date
    ? formatReleaseDate(
        {
          release_date: value.date,
          release_date_end: null,
          release_precision: (value.precision ?? 'day') as Precision,
        },
        locale.value,
        t('dates.tba'),
      )
    : ''
const isDate = (change: Change) => ['release_date', 'first_release_date'].includes(change.field)

async function submit() {
  try {
    const { applied } = await apply.mutateAsync({
      workId: workId.value,
      source: source.value,
      id: externalId.value,
      changes: [...chosen.value],
    })
    toast.success(
      applied.length
        ? t('integrations.metadata.applied', { n: applied.length }, applied.length)
        : t('integrations.metadata.linkedOnly', { source: label.value }),
    )
    await router.push(back.value)
  } catch (e) {
    toast.error((e as Error).message)
  }
}
</script>

<template>
  <EditPage
    :title="t('integrations.metadata.titleWith', { source: label })"
    :description="t('integrations.metadata.reviewHint')"
    :back="back"
    :busy="apply.isPending.value"
    :save-label="t('integrations.metadata.apply', { n: chosen.size }, chosen.size)"
    @submit="submit"
  >
    <p v-if="preview.data.value" class="py-4 text-sm" data-testid="metadata-entry">
      <span class="font-medium">{{ work.data.value?.title }}</span>
      <span class="text-muted-foreground"> ← {{ label }}: </span>
      <span class="font-medium">{{ preview.data.value.title }}</span>
      <span class="tabular font-mono text-xs text-muted-foreground">
        #{{ preview.data.value.external_id }}</span
      >
    </p>

    <div v-if="preview.isPending.value" class="grid gap-2 py-6">
      <Skeleton v-for="i in 4" :key="i" class="h-16 rounded-md" />
    </div>
    <p v-else-if="preview.isError.value" class="py-6 text-sm text-destructive" role="alert">
      {{ preview.error.value?.message }}
    </p>
    <p
      v-else-if="!groups.length"
      class="py-6 text-sm text-muted-foreground"
      data-testid="no-changes"
    >
      {{ t('integrations.metadata.same', { source: label }) }}
    </p>

    <EditSection v-for="group in groups" :key="group.key" :title="group.title">
      <ul class="divide-y rounded-lg border bg-card sm:col-span-2">
        <li
          v-for="change in group.changes"
          :key="change.id"
          :data-testid="`change-${change.field}`"
        >
          <label class="flex cursor-pointer items-start gap-3 px-3 py-3">
            <Checkbox
              :model-value="chosen.has(change.id)"
              class="mt-0.5"
              :data-testid="`pick-${change.field}`"
              @update:model-value="(on) => toggle(change.id, on)"
            />
            <div class="grid min-w-0 flex-1 gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium">
                  {{ t(`integrations.metadata.fields.${change.field}`) }}
                </span>
                <Badge :variant="change.kind === 'differs' ? 'outline' : 'secondary'">
                  {{ t(`integrations.metadata.kinds.${change.kind}`) }}
                </Badge>
              </div>
              <div class="grid gap-2 text-sm sm:grid-cols-2">
                <div v-for="side in ['current', 'proposed'] as const" :key="side" class="min-w-0">
                  <p class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
                    {{ side === 'current' ? t('integrations.metadata.current') : label }}
                  </p>
                  <img
                    v-if="change.field === 'cover' && change[side].image"
                    :src="change[side].image!"
                    alt=""
                    class="mt-1 h-28 rounded-sm border object-cover"
                  />
                  <p
                    v-else-if="isDate(change) ? change[side].date : change[side].text"
                    class="line-clamp-3"
                    :class="[
                      isDate(change) && 'tabular font-mono',
                      side === 'current' && 'text-muted-foreground',
                    ]"
                  >
                    {{ isDate(change) ? dateText(change[side]) : change[side].text }}
                  </p>
                  <p v-else class="text-muted-foreground">–</p>
                </div>
              </div>
            </div>
          </label>
        </li>
      </ul>
    </EditSection>
  </EditPage>
</template>
