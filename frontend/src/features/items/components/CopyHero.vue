<script setup lang="ts">
import { HandCoins, Image as ImageIcon, Pencil, RotateCcw, Trash2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import DetailHero from '@/components/app/DetailHero.vue'
import HeroStats from '@/components/app/HeroStats.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu'
import type { Item } from '@/api/types'
import { useProviders } from '@/features/library/composables/useReference'
import AddToListMenu from '@/features/lists/components/AddToListMenu.vue'
import { useAddonFigures } from '@/addons'
import ActiveLoan from './ActiveLoan.vue'
import { useItemMutations } from '../composables/useItem'

/** The top of a copy: cover, what it is, its figures (value, paid, change, since, play
 * time on its platform – from add-ons), its actions, and the loan while it's lent. The copy's
 * page and the explorer's column share it. `compact` (the column): only the add-ons' figures (the copy's card below has the rest), "edit" in the menu. */
const props = defineProps<{
  item: Item
  libraryId: string
  editable: boolean
  compact?: boolean
}>()
const emit = defineEmits<{ remove: [] }>()
const { t, n, d } = useI18n()
const { giveBack } = useItemMutations(() => props.libraryId)
const providers = useProviders()
const coverSources = computed(() =>
  (providers.data.value ?? []).some((p) => p.kind === 'covers' && p.enabled),
)
// Add-ons' figures (e.g. play time) belong to the game and platform, not the copy.
const addonFigures = useAddonFigures(() => ({
  workId: props.item.release.work_id,
  platformId: props.item.release.platform.id,
}))

/** Value now against what was paid: the change in percent. */
const stats = computed(() => {
  const copy = props.item
  const now = Number(copy.current_value) || 0
  const paid = Number(copy.purchase_price) || 0
  const change = now && paid ? Math.round(((now - paid) / paid) * 100) : null
  const since = copy.acquired_on ?? copy.created_at.slice(0, 10)
  if (props.compact) return addonFigures.value
  return [
    ...(now
      ? [{ key: 'value', label: t('items.stats.value'), value: n(now, 'currency'), accent: true }]
      : []),
    ...(paid ? [{ key: 'paid', label: t('items.stats.paid'), value: n(paid, 'currency') }] : []),
    ...(change !== null
      ? [
          {
            key: 'change',
            label: t('items.stats.change'),
            value: `${change > 0 ? '+' : ''}${n(change)} %`,
            tone: change >= 0 ? ('up' as const) : ('down' as const),
          },
        ]
      : []),
    {
      key: 'since',
      // The purchase date if it's known, else when the copy was entered here.
      label: copy.acquired_on ? t('items.stats.acquired') : t('items.stats.added'),
      value: d(new Date(since), 'short'),
    },
    ...addonFigures.value,
  ]
})

async function returnLoan(loanId: string) {
  await giveBack.mutateAsync(loanId)
  toast.success(t('items.returned'))
}
</script>

<template>
  <DetailHero
    testid="item"
    :title="item.title"
    :cover="{ src: item.cover_url, aspect: item.cover_aspect }"
    :manufacturer="item.release.platform.manufacturer"
    :menu-label="t('works.copyActions')"
  >
    <template #badges>
      <PlatformBadge :platform="item.release.platform" />
      <Badge variant="outline" class="font-mono text-[11px] uppercase">
        {{ item.release.region }}
      </Badge>
      <Badge v-if="item.release.edition" variant="secondary">
        {{ item.release.edition }}
      </Badge>
      <Badge
        v-if="item.overrides.length"
        variant="outline"
        :title="
          t('items.overrides.current', {
            fields: item.overrides.map((f) => t(`items.overrides.fields.${f}`)).join(', '),
          })
        "
        data-testid="own-values"
      >
        {{ t('items.overrides.badge') }}
      </Badge>
      <!-- Owned is the normal case: only say when it's sold. -->
      <Badge v-if="item.status !== 'owned'" variant="outline" data-testid="item-status">
        {{ t(`choices.status.${item.status}`) }}
      </Badge>
    </template>
    <template #menu>
      <template v-if="editable">
        <DropdownMenuItem v-if="compact" as-child>
          <RouterLink
            data-testid="edit-copy"
            :to="{ name: 'item-edit', params: { itemId: item.id } }"
          >
            <Pencil class="size-4" /> {{ t('items.editCopy') }}
          </RouterLink>
        </DropdownMenuItem>
        <DropdownMenuItem v-if="!item.active_loan" as-child>
          <RouterLink
            data-testid="lend-copy"
            :to="{ name: 'item-lend', params: { itemId: item.id } }"
          >
            <HandCoins class="size-4" /> {{ t('items.lend') }}
          </RouterLink>
        </DropdownMenuItem>
        <DropdownMenuItem
          v-else
          data-testid="return-copy"
          @select="returnLoan(item.active_loan.id)"
        >
          <RotateCcw class="size-4" /> {{ t('items.giveBack') }}
        </DropdownMenuItem>
        <DropdownMenuItem v-if="coverSources" as-child>
          <RouterLink
            data-testid="find-cover"
            :to="{
              name: 'cover-search',
              params: { releaseId: item.release.id },
              query: { back: $route.fullPath, item: item.id },
            }"
          >
            <ImageIcon class="size-4" /> {{ t('integrations.covers.search') }}
          </RouterLink>
        </DropdownMenuItem>
      </template>
      <AddToListMenu sub :release-id="item.release.id" :item-id="item.id" />
      <template v-if="editable">
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" data-testid="delete-copy" @select="emit('remove')">
          <Trash2 class="size-4" /> {{ t('works.deleteCopy') }}
        </DropdownMenuItem>
      </template>
    </template>
    <HeroStats :extra="stats" />
    <div v-if="editable && !compact" class="flex flex-wrap gap-2">
      <Button as-child data-testid="edit-copy">
        <RouterLink :to="{ name: 'item-edit', params: { itemId: item.id } }">
          <Pencil class="size-4" /> {{ t('items.editCopy') }}
        </RouterLink>
      </Button>
    </div>
    <ActiveLoan
      v-if="item.active_loan"
      :loan="item.active_loan"
      :editable="editable"
      @give-back="returnLoan"
    />
  </DetailHero>
</template>
