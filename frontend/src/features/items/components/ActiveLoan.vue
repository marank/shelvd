<script setup lang="ts">
import { HandCoins, RotateCcw } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import type { Item } from '@/api/types'
import { cn } from '@/lib/utils'

/** Who has the copy, since when, until when (red when overdue), and "give back". */
const props = defineProps<{ loan: NonNullable<Item['active_loan']>; editable: boolean }>()
const emit = defineEmits<{ giveBack: [loanId: string] }>()
const { t, d } = useI18n()
const today = new Date().toISOString().slice(0, 10)
const overdue = computed(() => !!props.loan.due_on && props.loan.due_on < today)
const date = (value: string) => d(new Date(value), 'short')
</script>

<template>
  <div
    data-testid="active-loan"
    :class="
      cn(
        'flex flex-wrap items-center gap-2 rounded-md border p-2 text-sm',
        overdue ? 'border-destructive/40 bg-destructive/10' : 'border-warning/40 bg-warning/10',
      )
    "
  >
    <HandCoins class="size-4" :class="overdue ? 'text-destructive' : 'text-warning'" />
    <span class="min-w-0 flex-1">
      {{ loan.borrower ? t('explorer.lentTo', { name: loan.borrower.name }) : t('items.lent') }}
      <span v-if="loan.lent_on" class="font-mono text-[11px] text-muted-foreground">
        · {{ t('items.since', { date: date(loan.lent_on) }) }}
        <template v-if="loan.due_on">
          ·
          <span :class="overdue && 'font-semibold text-destructive'">
            {{ t(overdue ? 'items.overdue' : 'items.due', { date: date(loan.due_on) }) }}
          </span>
        </template>
      </span>
    </span>
    <Button
      v-if="editable"
      size="sm"
      variant="outline"
      data-testid="return-button"
      @click="emit('giveBack', loan.id)"
    >
      <RotateCcw class="size-4" /> {{ t('items.giveBack') }}
    </Button>
  </div>
</template>
