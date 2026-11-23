import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import type { Item } from '@/api/types'
import { useItemMutations } from '@/features/items/composables/useItem'

/** How many copies this library has of each release (release id → count). */
export function copiesPerRelease(copies: MaybeRefOrGetter<Item[]>) {
  return computed(() => {
    const counts: Record<string, number> = {}
    for (const copy of toValue(copies)) counts[copy.release.id] = (counts[copy.release.id] ?? 0) + 1
    return counts
  })
}

/** What a game's and a release's page do with copies: add one (then edit it), give one back. */
export function useCopyActions(libraryId: MaybeRefOrGetter<string>) {
  const { t } = useI18n()
  const router = useRouter()
  const mutations = useItemMutations(libraryId)

  async function addCopy(releaseId: string) {
    const item = await mutations.create.mutateAsync(releaseId)
    toast.success(t('works.copyAdded'))
    void router.push({ name: 'item-edit', params: { itemId: item.id } })
  }
  async function giveBack(loanId: string) {
    await mutations.giveBack.mutateAsync(loanId)
    toast.success(t('items.returned'))
  }
  return { addCopy, giveBack }
}
