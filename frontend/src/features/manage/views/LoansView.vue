<script setup lang="ts">
import { Handshake, Trash2, Undo2 } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useRoute, useRouter } from 'vue-router'
import type { Loan } from '@/api/types'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { usePlatforms } from '@/features/library/composables/useReference'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import { errorMessage, formatDate, todayIso } from '../composables/format'
import { useLoanMutations, useLoans } from '../composables/useLoans'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const libraryId = computed(() => String(route.params.libraryId ?? ''))
const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))

const tab = ref<'open' | 'history'>('open')
const openLoans = useLoans(libraryId, true)
const history = useLoans(libraryId, false)
const current = computed(() => (tab.value === 'open' ? openLoans : history))
const rows = computed(() => current.value.data.value ?? [])
const overdueCount = computed(() => (openLoans.data.value ?? []).filter((l) => l.overdue).length)

const platforms = usePlatforms()
function platformOf(loan: Loan) {
  const found = platforms.data.value?.find(
    (p) => p.name === loan.platform || p.short_name === loan.platform,
  )
  return found ?? { name: loan.platform, short_name: loan.platform, manufacturer: '' }
}
function manufacturerOf(loan: Loan) {
  return platformOf(loan).manufacturer
}

const date = (value: string | null | undefined) => formatDate(value, locale.value)

function openItem(loan: Loan) {
  void router.push({
    name: 'explorer',
    params: { libraryId: libraryId.value },
    query: { item: loan.item_id },
  })
}

const { markReturned, remove } = useLoanMutations(libraryId)

// Mark returned: inline in the row, with today's date preset
const returning = ref<string | null>(null)
const returnDate = ref(todayIso())
function startReturn(loan: Loan) {
  returning.value = loan.id
  returnDate.value = todayIso()
}
async function confirmReturn(loan: Loan) {
  try {
    await markReturned.mutateAsync({ id: loan.id, returnedOn: returnDate.value })
    toast.success(t('manage.loans.returned', { title: loan.item_title }))
    returning.value = null
  } catch (e) {
    toast.error(errorMessage(e, t('errors.generic')))
  }
}

// Delete
const deleting = ref<Loan | null>(null)
const deleteError = ref('')
const deleteOpen = computed({
  get: () => !!deleting.value,
  set: (value) => {
    if (!value) deleting.value = null
  },
})
function startDelete(loan: Loan) {
  deleting.value = loan
  deleteError.value = ''
}
async function confirmDelete() {
  const loan = deleting.value
  if (!loan) return
  deleteError.value = ''
  try {
    await remove.mutateAsync(loan.id)
    toast.success(t('manage.loans.deleted'))
    deleting.value = null
  } catch (e) {
    deleteError.value = errorMessage(e, t('errors.generic'))
  }
}
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col" data-testid="LoansView">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t('manage.loans.title') }}</h1>
        <p class="text-sm text-muted-foreground" data-testid="loan-summary">
          <span class="font-mono tabular-nums">{{ openLoans.data.value?.length ?? 0 }}</span>
          {{ t('manage.loans.openCount', openLoans.data.value?.length ?? 0) }}
          <template v-if="overdueCount">
            ·
            <span class="font-mono text-destructive tabular-nums">{{ overdueCount }}</span>
            <span class="text-destructive">{{ t('manage.loans.overdueCount', overdueCount) }}</span>
          </template>
        </p>
      </div>
      <Tabs v-model="tab">
        <TabsList>
          <TabsTrigger value="open" data-testid="tab-open">{{
            t('manage.loans.open')
          }}</TabsTrigger>
          <TabsTrigger value="history" data-testid="tab-history">
            {{ t('manage.loans.history') }}
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </header>

    <div class="p-4 md:px-6">
      <div v-if="current.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="current.isError.value" variant="destructive">
        <AlertDescription>{{
          errorMessage(current.error.value, t('errors.generic'))
        }}</AlertDescription>
      </Alert>
      <Empty v-else-if="!rows.length" class="border" data-testid="loans-empty">
        <EmptyHeader>
          <EmptyMedia variant="icon"><Handshake /></EmptyMedia>
          <EmptyTitle>
            {{ tab === 'open' ? t('manage.loans.emptyOpen') : t('manage.loans.emptyHistory') }}
          </EmptyTitle>
          <EmptyDescription>{{ t('manage.loans.emptyHint') }}</EmptyDescription>
        </EmptyHeader>
      </Empty>
      <ul v-else class="divide-y rounded-lg border bg-card">
        <li
          v-for="loan in rows"
          :key="loan.id"
          data-testid="loan-row"
          role="button"
          tabindex="0"
          class="flex cursor-pointer flex-col gap-3 p-3 hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:flex-row sm:items-center"
          @click="openItem(loan)"
          @keydown.enter="openItem(loan)"
        >
          <div class="flex min-w-0 flex-1 items-center gap-3">
            <CoverImage
              fit="box"
              :src="loan.cover_url"
              :title="loan.item_title"
              :manufacturer="manufacturerOf(loan)"
              class="w-10 shrink-0"
            />
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="truncate font-medium">{{ loan.item_title }}</span>
                <PlatformBadge :platform="platformOf(loan)" />
                <Badge v-if="loan.overdue && !loan.returned_on" variant="destructive">
                  {{ t('manage.loans.overdue') }}
                </Badge>
              </div>
              <div class="truncate text-sm text-muted-foreground">
                {{ t('manage.loans.lentTo', { name: loan.borrower.name }) }}
              </div>
            </div>
          </div>
          <dl class="grid grid-cols-3 gap-x-4 gap-y-0.5 text-sm sm:w-auto sm:shrink-0">
            <div>
              <dt class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
                {{ t('manage.loans.lentOn') }}
              </dt>
              <dd class="font-mono tabular-nums">{{ date(loan.lent_on) }}</dd>
            </div>
            <div>
              <dt class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
                {{ t('manage.loans.dueOn') }}
              </dt>
              <dd
                class="font-mono tabular-nums"
                :class="{ 'font-medium text-destructive': loan.overdue && !loan.returned_on }"
                data-testid="loan-due"
              >
                {{ date(loan.due_on) || t('common.none') }}
              </dd>
            </div>
            <div>
              <dt class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
                {{ t('manage.loans.returnedOn') }}
              </dt>
              <dd class="font-mono tabular-nums">
                {{ date(loan.returned_on) || t('common.none') }}
              </dd>
            </div>
          </dl>
          <div
            v-if="editable"
            class="flex flex-wrap gap-1 sm:shrink-0"
            @click.stop
            @keydown.enter.stop
          >
            <form
              v-if="returning === loan.id"
              class="flex flex-wrap items-center gap-1"
              data-testid="return-form"
              @submit.prevent="confirmReturn(loan)"
            >
              <Input
                v-model="returnDate"
                type="date"
                class="h-8 w-36"
                :aria-label="t('manage.loans.returnedOn')"
                data-testid="return-date"
              />
              <Button
                type="submit"
                size="sm"
                data-testid="return-confirm"
                :disabled="markReturned.isPending.value"
              >
                <Spinner v-if="markReturned.isPending.value" />
                {{ t('actions.confirm') }}
              </Button>
              <Button type="button" variant="ghost" size="sm" @click="returning = null">
                {{ t('actions.cancel') }}
              </Button>
            </form>
            <Button
              v-else-if="!loan.returned_on"
              variant="outline"
              size="sm"
              data-testid="loan-return"
              @click="startReturn(loan)"
            >
              <Undo2 />
              {{ t('manage.loans.markReturned') }}
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              data-testid="loan-delete"
              :aria-label="t('actions.delete')"
              @click="startDelete(loan)"
            >
              <Trash2 />
            </Button>
          </div>
        </li>
      </ul>
    </div>

    <ConfirmDialog
      v-model:open="deleteOpen"
      :title="t('manage.loans.deleteTitle')"
      :description="t('manage.loans.deleteHint', { title: deleting?.item_title ?? '' })"
      :busy="remove.isPending.value"
      :error="deleteError"
      @confirm="confirmDelete"
    />
  </div>
</template>
