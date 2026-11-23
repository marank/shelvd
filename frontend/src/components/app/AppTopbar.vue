<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { onKeyStroke } from '@vueuse/core'
import { Plus, Search, X } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { canEdit } from '@/features/library/composables/useLibraries'
import { useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const route = useRoute()
/** On Upcoming, adding puts the game there; elsewhere the dialog decides by release. */
const destination = computed(() => (route.name === 'upcoming' ? 'track' : null))
const router = useRouter()
const ui = useUiStore()
const auth = useAuthStore()
const { id: libraryId, library } = useCurrentLibrary()

const input = ref<HTMLInputElement | null>(null)
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
watch(
  () => route.query.q,
  (q) => (query.value = typeof q === 'string' ? q : ''),
)

let timer: ReturnType<typeof setTimeout> | undefined
watch(query, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => search(value), 250)
})

function search(value: string) {
  if (!libraryId.value) return
  const onExplorer = route.name === 'explorer'
  if (!onExplorer && !value) return
  const nextQuery = { ...(onExplorer ? route.query : {}), q: value || undefined }
  const target = { name: 'explorer', params: { libraryId: libraryId.value }, query: nextQuery }
  if (onExplorer) void router.replace(target)
  else void router.push(target)
}

// "/" focuses the search like in most tools; Escape clears it.
onKeyStroke('/', (event) => {
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA'].includes(target.tagName)) return
  event.preventDefault()
  input.value?.focus()
})
</script>

<template>
  <header
    class="sticky top-0 z-20 flex h-12 shrink-0 items-center gap-2 border-b bg-background/85 px-3 backdrop-blur"
  >
    <SidebarTrigger class="-ml-1" />
    <Separator orientation="vertical" class="mr-1 h-5!" />
    <label
      class="relative flex h-8 max-w-xl min-w-0 flex-1 items-center rounded-md border bg-muted/40 pr-1 pl-8 focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/30"
    >
      <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
      <span class="sr-only">{{ t('actions.search') }}</span>
      <input
        ref="input"
        v-model="query"
        type="search"
        data-testid="global-search"
        class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground [&::-webkit-search-cancel-button]:hidden"
        :placeholder="t('topbar.searchPlaceholder')"
        @keydown.esc="query = ''"
      />
      <button
        v-if="query"
        type="button"
        class="rounded p-1 text-muted-foreground hover:text-foreground"
        :aria-label="t('actions.close')"
        @click="query = ''"
      >
        <X class="size-3.5" />
      </button>
      <Kbd v-else class="hidden sm:inline-flex">/</Kbd>
    </label>
    <div class="ml-auto flex items-center gap-1.5">
      <Button
        v-if="destination === 'track' ? auth.canContribute : libraryId && canEdit(library?.role)"
        size="sm"
        data-testid="add-button"
        @click="ui.openAdd(libraryId ?? '', 'search', destination)"
      >
        <Plus class="size-4" />
        <span class="hidden sm:inline">{{ t('actions.addGame') }}</span>
      </Button>
    </div>
  </header>
</template>
