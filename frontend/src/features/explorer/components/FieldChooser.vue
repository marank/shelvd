<script setup lang="ts">
import { Check, Search } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Input } from '@/components/ui/input'
import { FIELD_KEYS, LEVELS, fieldsOf, useFieldLabel, type ItemFieldKey } from '@/lib/itemFields'
import { cn } from '@/lib/utils'

/** Left half of the fields and sort dialogs: every field, grouped by copy / release /
 * game and their objects (Ort › Typ …), as toggles. The search understands paths
 * ("ort.typ") as well as single words. */
const props = defineProps<{ selected: ItemFieldKey[]; exclude?: ItemFieldKey[]; full?: boolean }>()
const emit = defineEmits<{ toggle: [key: ItemFieldKey] }>()
const { t } = useI18n()
const label = useFieldLabel()
const query = ref('')

const groups = computed(() => {
  const keys = FIELD_KEYS.filter(
    (key) => !props.exclude?.includes(key) && label.matches(key, query.value),
  )
  return LEVELS.map((level) => ({ ...level, objects: fieldsOf(level.key, keys) })).filter(
    (g) => g.objects.length,
  )
})
</script>

<template>
  <div class="grid content-start gap-3 md:-m-1 md:h-[26.5rem] md:overflow-y-auto md:p-1">
    <label class="relative flex items-center">
      <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
      <span class="sr-only">{{ t('explorer.searchFields') }}</span>
      <Input
        v-model="query"
        class="h-8 pl-8"
        data-testid="field-search"
        :placeholder="t('explorer.searchFields')"
      />
    </label>
    <div v-for="group in groups" :key="group.key" :data-testid="`field-level-${group.key}`">
      <p
        class="mb-1 flex items-center gap-1.5 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
      >
        <component :is="group.icon" class="size-3.5" />
        {{ t(`levels.${group.key}`) }}
        <span class="normal-case tracking-normal">· {{ t(`scopes.${group.scope}`) }}</span>
      </p>
      <div class="grid gap-1.5">
        <div
          v-for="cluster in group.objects"
          :key="cluster.object"
          class="flex flex-wrap items-center gap-1"
          :data-testid="`field-object-${cluster.object}`"
        >
          <span v-if="!cluster.loose" class="mr-0.5 w-20 shrink-0 text-xs text-muted-foreground">
            {{ label.object(cluster.object) }} ›
          </span>
          <button
            v-for="key in cluster.fields"
            :key="key"
            type="button"
            role="checkbox"
            :aria-checked="selected.includes(key)"
            :aria-label="label(key)"
            :disabled="full && !selected.includes(key)"
            :data-testid="`field-${key}`"
            :class="
              cn(
                'inline-flex h-7 items-center gap-1 rounded-md border px-2 text-xs disabled:opacity-40',
                selected.includes(key)
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'text-muted-foreground enabled:hover:bg-muted',
              )
            "
            @click="emit('toggle', key)"
          >
            <Check class="size-3" :class="!selected.includes(key) && 'invisible'" />
            {{ cluster.loose ? label(key) : label.short(key) }}
          </button>
        </div>
      </div>
    </div>
    <p v-if="!groups.length" class="text-sm text-muted-foreground">
      {{ t('explorer.noFieldMatch') }}
    </p>
  </div>
</template>
