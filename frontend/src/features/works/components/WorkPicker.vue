<script setup lang="ts">
import { Check, Search } from '@lucide/vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { useWorkSearch } from '../composables/useMerge'

/** Search a game by title and pick one (v-model = its id). */
const props = defineProps<{ exclude: string; initialQuery?: string }>()
const selected = defineModel<string>({ default: '' })
const { t } = useI18n()
const query = ref(props.initialQuery ?? '')
const results = useWorkSearch(query, () => props.exclude)
</script>

<template>
  <div class="grid gap-2" data-testid="work-picker">
    <label class="relative flex items-center">
      <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
      <span class="sr-only">{{ t('works.searchGame') }}</span>
      <Input
        v-model="query"
        class="pl-8"
        data-testid="work-search"
        :placeholder="t('works.searchGame')"
      />
    </label>
    <ul v-if="results.data.value?.length" class="divide-y rounded-lg border bg-card" role="listbox">
      <li v-for="work in results.data.value" :key="work.id">
        <button
          type="button"
          role="option"
          :aria-selected="selected === work.id"
          data-testid="work-option"
          :class="
            cn(
              'flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-accent/50',
              selected === work.id && 'bg-accent',
            )
          "
          @click="selected = work.id"
        >
          <CoverImage :src="work.cover_url" :title="work.title" fit="box" class="w-10 shrink-0" />
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-medium">{{ work.title }}</span>
            <span class="block truncate font-mono text-[11px] text-muted-foreground">
              {{ work.platforms.join(', ') || '—' }} ·
              {{ t('works.releaseCount', { n: work.releases }, work.releases) }}
            </span>
          </span>
          <Check v-if="selected === work.id" class="size-4 text-primary" />
        </button>
      </li>
    </ul>
    <p
      v-else-if="query.trim().length >= 2 && results.isSuccess.value"
      class="text-sm text-muted-foreground"
      data-testid="no-games"
    >
      {{ t('works.noGames') }}
    </p>
  </div>
</template>
