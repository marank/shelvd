import { describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { useRelease } from '@/features/items/composables/useItem'
import { useUpdateWork, useWorkCover } from '@/features/works/composables/useWork'
import { makeRelease, makeWork } from '@/test/fixtures'
import { mockApi, renderComponent } from '@/test/utils'

describe('work mutations', () => {
  it("refetch the game's releases (they carry its title and cover)", async () => {
    const calls = mockApi({
      'GET /api/catalog/releases/rel-1': makeRelease({ id: 'rel-1' }),
      'PATCH /api/catalog/works/work-1': makeWork(),
      'DELETE /api/catalog/works/work-1/cover': { status: 204 },
    })
    let update!: ReturnType<typeof useUpdateWork>
    let cover!: ReturnType<typeof useWorkCover>
    const Host = defineComponent({
      setup() {
        useRelease('rel-1')
        update = useUpdateWork('work-1')
        cover = useWorkCover('work-1')
        return () => null
      },
    })
    await renderComponent(Host)
    const reads = () => calls.filter((c) => c.method === 'GET' && c.path.endsWith('/rel-1'))
    expect(reads()).toHaveLength(1)
    await update.mutateAsync({ title: 'New' })
    await vi.waitFor(() => expect(reads()).toHaveLength(2))
    await cover.remove.mutateAsync()
    await vi.waitFor(() => expect(reads()).toHaveLength(3))
  })
})
