import { describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { keys } from '@/features/library/composables/queryKeys'
import {
  useItem,
  useItemMutations,
  useRelease,
  useReleaseMutations,
} from '@/features/items/composables/useItem'
import { makeItem, makeRelease } from '@/test/fixtures'
import { mockApi, renderComponent, settle } from '@/test/utils'

/** A component that only runs `run` in its setup, to use composables there. */
const host = (run: () => void) =>
  defineComponent({
    setup() {
      run()
      return () => null
    },
  })

const release = makeRelease({ id: 'rel-1' })
const item = makeItem({ id: 'item-1', release })

describe('item and release mutations', () => {
  it('refetch the release after a release change (no stale form on the next edit)', async () => {
    const calls = mockApi({
      'GET /api/catalog/releases/rel-1': release,
      'PATCH /api/catalog/releases/rel-1': release,
      'POST /api/catalog/releases/rel-1/barcodes': release,
    })
    let mutations!: ReturnType<typeof useReleaseMutations>
    await renderComponent(
      host(() => {
        useRelease('rel-1')
        mutations = useReleaseMutations('lib-1')
      }),
    )
    const reads = () => calls.filter((c) => c.method === 'GET' && c.path.endsWith('/rel-1'))
    expect(reads()).toHaveLength(1)
    await mutations.update.mutateAsync({ id: 'rel-1', body: { title: 'New' } })
    await vi.waitFor(() => expect(reads()).toHaveLength(2))
    await mutations.addBarcode.mutateAsync({ id: 'rel-1', code: '4006381333931' })
    await vi.waitFor(() => expect(reads()).toHaveLength(3))
  })

  it("drops a deleted copy's own query instead of refetching it", async () => {
    const calls = mockApi({
      'GET /api/libraries/lib-1/items/item-1': item,
      'DELETE /api/libraries/lib-1/items/item-1': { status: 204 },
    })
    let mutations!: ReturnType<typeof useItemMutations>
    const { queryClient } = await renderComponent(
      host(() => {
        useItem('lib-1', 'item-1')
        mutations = useItemMutations('lib-1')
      }),
    )
    expect(queryClient.getQueryData(keys.item('lib-1', 'item-1'))).toEqual(item)
    await mutations.remove.mutateAsync('item-1')
    await settle()
    expect(queryClient.getQueryData(keys.item('lib-1', 'item-1'))).toBeUndefined()
    expect(calls.filter((c) => c.method === 'GET' && c.path.endsWith('/item-1'))).toHaveLength(1)
  })
})
