<script setup lang="ts">
import { Library as LibraryIcon } from '@lucide/vue'
import { ref, watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { useCurrentLibrary } from '../composables/useCurrentLibrary'
import { useCreateLibrary } from '../composables/useLibraries'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { id, libraries } = useCurrentLibrary()
const create = useCreateLibrary()
const name = ref('')

// With a library to show and no "new" request, go straight to it.
watchEffect(() => {
  if (id.value && route.query.new !== '1') {
    void router.replace({ name: 'explorer', params: { libraryId: id.value } })
  }
})

async function submit() {
  const library = await create.mutateAsync({ name: name.value || t('library.defaultName') })
  void router.push({ name: 'explorer', params: { libraryId: library.id } })
}
</script>

<template>
  <div class="flex flex-1 items-center justify-center p-6">
    <Spinner v-if="libraries.isPending.value" class="size-6" />
    <Empty v-else class="max-w-md border">
      <EmptyHeader>
        <EmptyMedia variant="icon"><LibraryIcon /></EmptyMedia>
        <EmptyTitle>
          {{ libraries.data.value?.length ? t('nav.newLibrary') : t('library.welcomeTitle') }}
        </EmptyTitle>
        <EmptyDescription>{{ t('library.welcomeText') }}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <form class="flex w-full gap-2" @submit.prevent="submit">
          <Input
            v-model="name"
            data-testid="library-name"
            :placeholder="t('library.defaultName')"
            :aria-label="t('fields.name')"
          />
          <Button type="submit" :disabled="create.isPending.value">{{
            t('actions.create')
          }}</Button>
        </form>
      </EmptyContent>
    </Empty>
  </div>
</template>
