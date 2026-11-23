<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import DangerZoneCard from '../components/settings/DangerZoneCard.vue'
import GeneralCard from '../components/settings/GeneralCard.vue'
import ImportCard from '../components/settings/ImportCard.vue'
import MembersCard from '../components/settings/MembersCard.vue'
import PublicLinkCard from '../components/settings/PublicLinkCard.vue'
import { errorMessage } from '../composables/format'

const { t } = useI18n()
const route = useRoute()
const libraryId = computed(() => String(route.params.libraryId ?? ''))
const library = useLibrary(libraryId)
const isOwner = computed(() => library.data.value?.role === 'owner')
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col" data-testid="LibrarySettingsView">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t('manage.settings.title') }}</h1>
        <p class="truncate text-sm text-muted-foreground">{{ library.data.value?.name }}</p>
      </div>
    </header>
    <div class="p-4 md:px-6">
      <div v-if="library.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="library.isError.value" variant="destructive">
        <AlertDescription>{{
          errorMessage(library.error.value, t('errors.generic'))
        }}</AlertDescription>
      </Alert>
      <div v-else-if="library.data.value" class="mx-auto grid max-w-3xl gap-4">
        <GeneralCard :library="library.data.value" :is-owner="isOwner" />
        <MembersCard :library="library.data.value" :is-owner="isOwner" />
        <ImportCard v-if="canEdit(library.data.value.role)" :library="library.data.value" />
        <PublicLinkCard v-if="isOwner" :library="library.data.value" />
        <DangerZoneCard v-if="isOwner" :library="library.data.value" />
      </div>
    </div>
  </div>
</template>
