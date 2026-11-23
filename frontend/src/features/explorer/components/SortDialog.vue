<script setup lang="ts">
import { ArrowDownWideNarrow, ArrowUpNarrowWide } from '@lucide/vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useFieldLabel, type SortLevel } from '@/lib/itemFields'
import SortPicker from './SortPicker.vue'

/** A view's sort, chosen in a dialog that looks like the fields dialog. Opened from the
 * view bar and the view edit page; works on a draft that "Apply" hands back. */
const model = defineModel<SortLevel[]>({ required: true })
const { t } = useI18n()
const label = useFieldLabel()
const open = ref(false)
const draft = ref<SortLevel[]>([])

function onOpen(value: boolean) {
  if (value) draft.value = model.value.map((l) => ({ ...l }))
  open.value = value
}
function apply() {
  model.value = draft.value
  open.value = false
}
</script>

<template>
  <Dialog :open="open" @update:open="onOpen">
    <DialogTrigger as-child>
      <slot>
        <Button
          variant="outline"
          size="sm"
          class="h-8 max-w-56 gap-1 text-xs"
          data-testid="sort-button"
          :aria-label="t('explorer.sortTitle')"
        >
          <ArrowDownWideNarrow v-if="model[0]?.desc" class="size-4" />
          <ArrowUpNarrowWide v-else class="size-4" />
          <span class="truncate">{{ label(model[0]?.key ?? 'game.title') }}</span>
          <span v-if="model.length > 1" class="font-mono text-muted-foreground">
            +{{ model.length - 1 }}
          </span>
        </Button>
      </slot>
    </DialogTrigger>
    <DialogContent class="max-h-[90svh] overflow-y-auto sm:max-w-4xl">
      <DialogHeader>
        <DialogTitle>{{ t('explorer.sortTitle') }}</DialogTitle>
        <DialogDescription>{{ t('explorer.sortHint') }}</DialogDescription>
      </DialogHeader>
      <SortPicker v-model="draft" />
      <DialogFooter>
        <Button type="button" variant="ghost" @click="open = false">
          {{ t('actions.cancel') }}
        </Button>
        <Button type="button" data-testid="apply-sort" @click="apply">
          {{ t('explorer.applyFields') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
