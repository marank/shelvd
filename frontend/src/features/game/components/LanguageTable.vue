<script setup lang="ts">
// The game's languages (IGDB): one row each, with what is in it – voices, subtitles,
// menus. The reader's language and English first; long lists show a few until opened.
import { Check } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useChoiceLabel } from '@/lib/itemFields'

const props = defineProps<{ languages: Record<string, string[]> }>()
const { t, locale } = useI18n()
const label = useChoiceLabel()
const KINDS = ['audio', 'subtitles', 'interface'] as const
const FIRST: Record<string, string> = { de: 'German', en: 'English' }
const SHOWN = 6

const rows = computed(() => {
  const mine = FIRST[locale.value.split('-')[0]!] ?? 'English'
  const rank = (name: string) => (name === mine ? 0 : name === 'English' ? 1 : 2)
  return Object.entries(props.languages)
    .map(([name, kinds]) => ({ name, label: label('language', name), kinds: new Set(kinds) }))
    .sort((a, b) => rank(a.name) - rank(b.name) || a.label.localeCompare(b.label))
})
const all = ref(false)
const visible = computed(() => (all.value ? rows.value : rows.value.slice(0, SHOWN)))
</script>

<template>
  <div v-if="rows.length" data-testid="language-table">
    <p class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
      {{ t('itemFields.game.languages') }}
    </p>
    <table class="w-full text-sm">
      <thead>
        <tr class="text-xs text-muted-foreground">
          <th class="py-1 text-left font-normal">
            <span class="sr-only">{{ t('itemFields.game.languages') }}</span>
          </th>
          <th v-for="kind in KINDS" :key="kind" class="w-20 py-1 text-center font-normal">
            {{ t(`game.languageKinds.${kind}`) }}
          </th>
        </tr>
      </thead>
      <tbody class="divide-y">
        <tr v-for="row in visible" :key="row.name" :data-language="row.name">
          <td class="py-1.5 pr-2">{{ row.label }}</td>
          <td v-for="kind in KINDS" :key="kind" class="py-1.5 text-center">
            <Check
              v-if="row.kinds.has(kind)"
              class="mx-auto size-4 text-primary"
              :aria-label="t(`game.languageKinds.${kind}`)"
            />
          </td>
        </tr>
      </tbody>
    </table>
    <button
      v-if="rows.length > SHOWN"
      type="button"
      class="mt-1 text-xs text-primary hover:underline"
      data-testid="languages-more"
      @click="all = !all"
    >
      {{ all ? t('game.fewerLanguages') : t('game.allLanguages', { n: rows.length }) }}
    </button>
  </div>
</template>
