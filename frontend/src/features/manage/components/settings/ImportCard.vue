<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { collect } from '@/addons'
import type { Library } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

/** Ways to bring a collection in from another app – add-ons bring them; without one, no card. */
defineProps<{ library: Library }>()
const { t } = useI18n()
const imports = collect('libraryImports').flat()
</script>

<template>
  <Card v-if="imports.length" data-testid="settings-import">
    <CardHeader>
      <CardTitle>{{ t('manage.settings.import') }}</CardTitle>
      <CardDescription>{{ t('manage.settings.importHint') }}</CardDescription>
    </CardHeader>
    <CardContent class="flex flex-wrap gap-2">
      <Button v-for="link in imports" :key="link.route" as-child variant="outline">
        <RouterLink
          :to="{ name: link.route, params: { libraryId: library.id } }"
          :data-testid="link.testid"
        >
          <component :is="link.icon" />
          {{ t(link.label) }}
        </RouterLink>
      </Button>
    </CardContent>
  </Card>
</template>
