<script setup lang="ts">
import { Columns3 } from '@lucide/vue'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DEFAULT_FIELDS, PRESENTATIONS, type Presentation, type ViewFields } from '@/lib/itemFields'
import FieldPicker from './FieldPicker.vue'

/** The one place to choose a view's fields, one tab per presentation (grid, list, table,
 * detail column). Opened from the view bar and the view edit page; works on a draft that
 * "Apply" hands back. */
const props = defineProps<{ initial: Presentation }>()
const model = defineModel<ViewFields>({ required: true })
const { t } = useI18n()
const open = ref(false)
const tab = ref<Presentation>(props.initial)
const draft = ref<ViewFields>({ ...model.value })

function onOpen(value: boolean) {
  if (value) {
    draft.value = { ...model.value }
    tab.value = props.initial
  }
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
        <Button variant="outline" size="sm" class="h-8 gap-1 text-xs" data-testid="fields-button">
          <Columns3 class="size-4" />
          <span class="hidden lg:inline">{{ t('explorer.fieldsButton') }}</span>
        </Button>
      </slot>
    </DialogTrigger>
    <DialogContent class="max-h-[90svh] overflow-y-auto sm:max-w-4xl">
      <DialogHeader>
        <DialogTitle>{{ t('explorer.fieldsTitle') }}</DialogTitle>
        <DialogDescription>{{ t('explorer.fieldsHint') }}</DialogDescription>
      </DialogHeader>
      <Tabs v-model="tab">
        <TabsList>
          <TabsTrigger
            v-for="p in PRESENTATIONS"
            :key="p"
            :value="p"
            :data-testid="`fields-tab-${p}`"
          >
            {{ t(`explorer.presentations.${p}`) }}
          </TabsTrigger>
        </TabsList>
        <TabsContent v-for="p in PRESENTATIONS" :key="p" :value="p" class="mt-3">
          <p class="mb-3 text-xs text-muted-foreground">
            {{ t(`explorer.presentationHints.${p}`) }}
          </p>
          <FieldPicker v-model="draft[p]" :defaults="DEFAULT_FIELDS[p]" />
        </TabsContent>
      </Tabs>
      <DialogFooter>
        <Button type="button" variant="ghost" @click="open = false">
          {{ t('actions.cancel') }}
        </Button>
        <Button type="button" data-testid="apply-fields" @click="apply">
          {{ t('explorer.applyFields') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
