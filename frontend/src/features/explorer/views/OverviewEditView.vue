<script setup lang="ts">
import { LayoutGrid, List, Sheet } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { GROUP_FIELDS, type GroupField } from '@/api/types'
import { cn } from '@/lib/utils'
import {
  PRESENTATIONS,
  formatSort,
  parseSort,
  useFieldLabel,
  knownFields,
  shownFields,
  viewFields,
  type ViewFields,
} from '@/lib/itemFields'
import { Button } from '@/components/ui/button'
import FieldsDialog from '../components/FieldsDialog.vue'
import SortDialog from '../components/SortDialog.vue'
import FilterEditor from '../components/FilterEditor.vue'
import { formatConditions, parseConditions, type Condition } from '@/lib/conditions'
import SectionPicker from '../components/SectionPicker.vue'
import GroupByEditor from '../components/GroupByEditor.vue'
import { useOverviews, useSaveOverview } from '../composables/useOverviews'
import type { Layout } from '../composables/useExplorerState'

/** Create a saved view (prefilled from the explorer's current state) or edit one. */
const { t } = useI18n()
const fieldLabel = useFieldLabel()
const route = useRoute()
const router = useRouter()
const libraryId = computed(() => String(route.params.libraryId))
const overviewId = computed(() => (route.params.overviewId ? String(route.params.overviewId) : ''))
const overviews = useOverviews(libraryId)
const { create, update } = useSaveOverview(libraryId)
const existing = computed(() => overviews.data.value?.find((o) => o.id === overviewId.value))

const layouts = [
  { value: 'grid', icon: LayoutGrid },
  { value: 'list', icon: List },
  { value: 'table', icon: Sheet },
] as const

function fromQuery() {
  const g = typeof route.query.g === 'string' ? route.query.g : ''
  const layout = String(route.query.layout ?? 'grid')
  return {
    name: typeof route.query.name === 'string' ? route.query.name : '',
    group_by: g.split(',').filter((f): f is GroupField => GROUP_FIELDS.includes(f as GroupField)),
    section: (GROUP_FIELDS.includes(route.query.s as GroupField) ? route.query.s : '') as
      GroupField | '',
    sort: parseSort(typeof route.query.sort === 'string' ? route.query.sort : ''),
    layout: (['grid', 'list', 'table'].includes(layout) ? layout : 'grid') as Layout,
    filters: [] as Condition[],
    match: 'all' as 'all' | 'any',
    fields: Object.fromEntries(
      PRESENTATIONS.map((p) => {
        const raw = route.query[`f_${p}`]
        return [p, knownFields(typeof raw === 'string' ? raw.split(',') : [])]
      }),
    ) as ViewFields,
  }
}

const form = reactive(fromQuery())
const loaded = ref(false)
watch(
  existing,
  (value) => {
    if (!value || loaded.value) return
    loaded.value = true
    Object.assign(form, {
      name: value.name,
      group_by: value.group_by as GroupField[],
      section: (GROUP_FIELDS.includes(value.section as GroupField) ? value.section : '') as
        GroupField | '',
      sort: parseSort(value.sort),
      layout: value.layout,
      filters: parseConditions(value.filters),
      match: value.match,
      fields: viewFields(value.fields),
    })
  },
  { immediate: true },
)

const back = computed(() => ({
  name: 'explorer',
  params: { libraryId: libraryId.value },
  query: overviewId.value ? { v: overviewId.value } : {},
}))
const error = ref('')
const busy = computed(() => create.isPending.value || update.isPending.value)

async function save() {
  error.value = ''
  if (!form.name.trim()) {
    error.value = t('explorer.nameRequired')
    return
  }
  // Empty field lists mean "defaults": no need to store them.
  const fields = Object.fromEntries(Object.entries(form.fields).filter(([, keys]) => keys.length))
  // Unfinished conditions (no value yet) are left out.
  const filters = formatConditions(form.filters)
  const body = {
    ...form,
    name: form.name.trim(),
    filters,
    fields,
    sort: formatSort(form.sort),
  }
  try {
    const saved = existing.value
      ? await update.mutateAsync({ id: existing.value.id, body })
      : await create.mutateAsync({
          ...body,
          position: (overviews.data.value?.length ?? 0) + 1,
        })
    toast.success(t('explorer.viewSaved'))
    void router.push({
      name: 'explorer',
      params: { libraryId: libraryId.value },
      query: { v: saved.id },
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}
</script>

<template>
  <EditPage
    v-if="!overviewId || existing"
    :title="existing ? t('explorer.editView') : t('explorer.newView')"
    :description="t('explorer.saveViewHint')"
    :back="back"
    :busy="busy"
    :error="error"
    @submit="save"
  >
    <EditSection :title="t('fields.name')">
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="v-name">{{ t('fields.name') }}</Label>
        <Input id="v-name" v-model="form.name" :placeholder="t('explorer.newViewPlaceholder')" />
      </div>
    </EditSection>
    <EditSection :title="t('explorer.nesting')" :description="t('explorer.nestingHint')">
      <div class="sm:col-span-2">
        <GroupByEditor v-model="form.group_by" />
      </div>
    </EditSection>
    <EditSection :title="t('explorer.sections')" :description="t('explorer.sectionsHint')">
      <div class="sm:col-span-2">
        <SectionPicker v-model="form.section" />
      </div>
    </EditSection>
    <EditSection :title="t('explorer.filters')" :description="t('explorer.filtersHint')">
      <div class="sm:col-span-2">
        <FilterEditor v-model="form.filters" v-model:match="form.match" :library-id="libraryId" />
      </div>
    </EditSection>
    <EditSection :title="t('explorer.fieldsTitle')" :description="t('explorer.fieldsHint')">
      <div class="sm:col-span-2">
        <ul class="divide-y rounded-lg border bg-card" data-testid="view-fields">
          <li
            v-for="p in PRESENTATIONS"
            :key="p"
            class="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-center"
            :data-testid="`view-fields-${p}`"
          >
            <span class="w-28 shrink-0 text-sm font-medium">
              {{ t(`explorer.presentations.${p}`) }}
            </span>
            <span class="flex min-w-0 flex-1 flex-wrap items-center gap-1">
              <span
                v-for="key in shownFields(form.fields, p)"
                :key="key"
                class="rounded-md border bg-background px-1.5 py-px text-xs"
              >
                {{ fieldLabel(key) }}
              </span>
              <span v-if="!form.fields[p].length" class="text-xs text-muted-foreground">
                ({{ t('explorer.resetFields') }})
              </span>
            </span>
            <FieldsDialog v-model="form.fields" :initial="p">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="self-start sm:self-center"
                :data-testid="`edit-fields-${p}`"
              >
                {{ t('actions.edit') }}
              </Button>
            </FieldsDialog>
          </li>
        </ul>
      </div>
    </EditSection>
    <EditSection :title="t('explorer.display')">
      <div class="grid gap-1.5">
        <span class="text-sm font-medium">{{ t('explorer.sortTitle') }}</span>
        <div class="flex flex-wrap items-center gap-1.5" data-testid="view-sort">
          <span
            v-for="(level, index) in form.sort.length
              ? form.sort
              : [{ key: 'game.title' as const, desc: false }]"
            :key="level.key"
            class="inline-flex items-center gap-1 rounded-md border bg-card px-1.5 py-px text-xs"
          >
            <span class="font-mono text-muted-foreground">{{ index + 1 }}</span>
            {{ fieldLabel(level.key) }}
            <span class="text-muted-foreground">{{ level.desc ? '↓' : '↑' }}</span>
          </span>
          <SortDialog v-model="form.sort">
            <Button type="button" variant="outline" size="sm" data-testid="edit-sort">
              {{ t('actions.edit') }}
            </Button>
          </SortDialog>
        </div>
      </div>
      <div class="grid gap-1.5">
        <span class="text-sm font-medium">{{ t('explorer.layout') }}</span>
        <div class="flex gap-1.5" role="radiogroup" :aria-label="t('explorer.layout')">
          <button
            v-for="l in layouts"
            :key="l.value"
            type="button"
            role="radio"
            :aria-checked="form.layout === l.value"
            :data-testid="`view-layout-${l.value}`"
            :class="
              cn(
                'flex h-9 flex-1 items-center justify-center gap-1.5 rounded-md border text-sm',
                form.layout === l.value
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'text-muted-foreground hover:bg-muted',
              )
            "
            @click="form.layout = l.value"
          >
            <component :is="l.icon" class="size-4" /> {{ t(`choices.layout.${l.value}`) }}
          </button>
        </div>
      </div>
    </EditSection>
  </EditPage>
  <div v-else-if="overviews.isSuccess.value" class="p-6 text-muted-foreground">
    {{ t('errors.notFound') }}
  </div>
</template>
