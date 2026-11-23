<script setup lang="ts">
// One section of the game page: a heading that folds it in and out (remembered), with a
// count, badges and actions beside it; the content below.
import { ChevronRight } from '@lucide/vue'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

defineProps<{ title: string; count?: number; testid: string }>()
const open = defineModel<boolean>('open', { required: true })
</script>

<template>
  <Collapsible v-model:open="open" as="section" :data-testid="testid">
    <div class="flex min-h-8 flex-wrap items-center gap-x-3 gap-y-2 border-b pb-2">
      <CollapsibleTrigger
        class="group flex min-w-0 flex-1 items-center gap-1.5 text-left text-sm font-semibold"
        :data-testid="`${testid}-toggle`"
      >
        <ChevronRight
          class="size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-90"
        />
        <span class="truncate">{{ title }}</span>
        <span
          v-if="count !== undefined"
          class="tabular font-mono font-normal text-muted-foreground"
        >
          · {{ count }}
        </span>
        <slot name="badges" />
      </CollapsibleTrigger>
      <div v-if="$slots.actions && open" class="flex flex-wrap items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <CollapsibleContent class="pt-4">
      <slot />
    </CollapsibleContent>
  </Collapsible>
</template>
