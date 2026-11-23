<script setup lang="ts">
import { Library as LibraryIcon, Plus, Settings, Share2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useLibraries } from '../composables/useLibraries'

/** All libraries you're a member of, each leading to itself and its settings. */
const { t } = useI18n()
const libraries = useLibraries()
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col" data-testid="LibrariesView">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t('nav.libraries') }}</h1>
        <p class="text-sm text-muted-foreground">{{ t('library.overview.subtitle') }}</p>
      </div>
      <Button as-child>
        <RouterLink :to="{ name: 'home', query: { new: '1' } }" data-testid="library-new">
          <Plus /> {{ t('nav.newLibrary') }}
        </RouterLink>
      </Button>
    </header>

    <div class="grid max-w-4xl gap-3 p-4 md:px-6">
      <div v-if="libraries.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="libraries.isError.value" variant="destructive">
        <AlertDescription>{{ libraries.error.value?.message }}</AlertDescription>
      </Alert>
      <ul v-else class="divide-y rounded-lg border bg-card">
        <li
          v-for="lib in libraries.data.value"
          :key="lib.id"
          class="flex flex-wrap items-center gap-3 p-3"
          data-testid="library-row"
        >
          <div class="flex size-9 shrink-0 items-center justify-center rounded-md border">
            <LibraryIcon class="size-4" />
          </div>
          <RouterLink
            :to="{ name: 'explorer', params: { libraryId: lib.id } }"
            class="min-w-0 flex-1 hover:underline"
          >
            <span class="block truncate font-medium">{{ lib.name }}</span>
            <span class="tabular block truncate font-mono text-[11px] text-muted-foreground">
              {{
                [
                  t('common.items', { n: lib.item_count }, lib.item_count),
                  t(`choices.role.${lib.role}`),
                  lib.role === 'owner' ? '' : lib.owner,
                ]
                  .filter(Boolean)
                  .join(' · ')
              }}
            </span>
          </RouterLink>
          <Badge v-if="lib.public_token" variant="secondary" class="gap-1">
            <Share2 class="size-3" /> {{ t('library.overview.public') }}
          </Badge>
          <Button as-child variant="outline" size="sm">
            <RouterLink
              :to="{ name: 'library-settings', params: { libraryId: lib.id } }"
              :data-testid="`library-settings-${lib.id}`"
            >
              <Settings class="size-4" /> {{ t('nav.settings') }}
            </RouterLink>
          </Button>
        </li>
      </ul>
    </div>
  </div>
</template>
