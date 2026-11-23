<script setup lang="ts">
import { Link2Off } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'

const { t } = useI18n()
</script>

<template>
  <Empty class="mx-auto mt-10 max-w-md border" data-testid="link-gone">
    <EmptyHeader>
      <EmptyMedia variant="icon"><Link2Off /></EmptyMedia>
      <EmptyTitle>{{ t('public.goneTitle') }}</EmptyTitle>
      <EmptyDescription>{{ t('public.goneText') }}</EmptyDescription>
    </EmptyHeader>
  </Empty>
</template>
