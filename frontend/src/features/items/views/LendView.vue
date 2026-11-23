<script setup lang="ts">
import ForbiddenView from '@/features/library/views/ForbiddenView.vue'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePeople } from '@/features/library/composables/useReference'
import ChoiceSelect from '../components/ChoiceSelect.vue'
import { useItemById, useItemMutations } from '../composables/useItem'

const NEW = '__new'
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const itemId = computed(() => String(route.params.itemId))
const { item, libraryId } = useItemById(itemId)
const people = usePeople(libraryId)
const { lend } = useItemMutations(libraryId)
const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))

const form = reactive<{ borrower: string | null; name: string; due_on: string; notes: string }>({
  borrower: NEW,
  name: '',
  due_on: '',
  notes: '',
})
const error = ref('')
const borrowerOptions = computed(() => [
  { value: NEW, label: t('items.newPerson') },
  ...(people.data.value ?? []).map((p) => ({ value: p.id, label: p.name })),
])
const back = computed(() => ({ name: 'item', params: { itemId: itemId.value } }))

async function submit() {
  error.value = ''
  const existing = form.borrower && form.borrower !== NEW ? form.borrower : null
  try {
    await lend.mutateAsync({
      item_id: itemId.value,
      borrower_id: existing,
      borrower_name: existing ? '' : form.name.trim(),
      due_on: form.due_on || null,
      notes: form.notes,
    })
    toast.success(t('items.lent'))
    void router.push(back.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}
</script>

<template>
  <ForbiddenView v-if="library.data.value && !editable" />
  <EditPage
    v-else-if="item.data.value"
    :title="t('items.lendTitle', { title: item.data.value.title })"
    :back="back"
    :busy="lend.isPending.value"
    :save-label="t('items.lend')"
    :error="error"
    @submit="submit"
  >
    <EditSection :title="t('fields.borrower')" :description="t('items.borrowerHint')">
      <div class="grid gap-1.5">
        <Label for="l-borrower">{{ t('fields.borrower') }}</Label>
        <ChoiceSelect id="l-borrower" v-model="form.borrower" :options="borrowerOptions" />
      </div>
      <div v-if="form.borrower === NEW" class="grid gap-1.5">
        <Label for="l-name">{{ t('fields.name') }}</Label>
        <!-- eslint-disable-next-line vuejs-accessibility/no-autofocus -- appears when the user picks a new borrower; the name is the next thing to type -->
        <Input id="l-name" v-model="form.name" autofocus />
      </div>
    </EditSection>
    <EditSection :title="t('items.loanDetails')">
      <div class="grid gap-1.5">
        <Label for="l-due">{{ t('items.dueOn') }}</Label>
        <Input id="l-due" v-model="form.due_on" type="date" />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="l-notes">{{ t('fields.notes') }}</Label>
        <Input id="l-notes" v-model="form.notes" />
      </div>
    </EditSection>
  </EditPage>
</template>
