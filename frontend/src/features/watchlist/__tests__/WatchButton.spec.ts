import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mockApi, renderComponent, settle } from '@/test/utils'
import WatchButton from '../components/WatchButton.vue'
import { $, tracking, upcoming } from './fixtures'

type Action = { label: string; onClick: () => void }
const toast = vi.hoisted(() => ({
  success: vi.fn<(message: string, options?: { action?: Action }) => void>(),
  error: vi.fn<(message: string) => void>(),
}))
vi.mock('vue-sonner', async (original) => ({ ...(await original<object>()), toast }))

const release = upcoming({ id: 'r-1', title: 'Metroid Prime 4' })

describe('WatchButton', () => {
  beforeEach(() => vi.clearAllMocks())

  it('watches an untracked release, without a library, and links to the entry', async () => {
    const calls = mockApi({
      'GET /api/watchlist': [tracking({ id: 't-other', release: upcoming({ id: 'r-2' }) })],
      'POST /api/watchlist': { status: 201, body: tracking({ id: 't-new', release }) },
    })
    const { router } = await renderComponent(WatchButton, { props: { releaseId: 'r-1' } })
    expect(calls[0]?.query.get('mine')).toBe('true')
    expect($('[data-testid="track-button"]').textContent).toContain('Watch')
    $('[data-testid="track-button"]').click()
    await settle()
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      release_id: 'r-1',
      status: 'watching',
      library_id: null,
      shop: '',
      notes: '',
    })
    const [message, options] = toast.success.mock.calls[0]!
    expect(message).toBe('“Metroid Prime 4” is now on Upcoming')
    expect(options?.action?.label).toBe('Open')
    options!.action!.onClick()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/watchlist/t-new/edit'))
  })

  it('reports errors when watching fails', async () => {
    mockApi({
      'GET /api/watchlist': [],
      'POST /api/watchlist': { status: 409, body: { detail: 'Already tracked.' } },
    })
    await renderComponent(WatchButton, { props: { releaseId: 'r-1' } })
    $('[data-testid="track-button"]').click()
    await settle()
    expect(toast.error).toHaveBeenCalledWith('Already tracked.')
  })

  it('shows a tracked release as a link to its entry (German)', async () => {
    mockApi({
      'GET /api/watchlist': [tracking({ id: 't-1', status: 'preordered', release })],
    })
    await renderComponent(WatchButton, {
      props: { releaseId: 'r-1' },
      url: '/works/w-1',
      locale: 'de',
    })
    await settle()
    const chip = $('[data-testid="track-chip"]')
    expect(chip.textContent).toContain('Vorbestellt')
    expect(chip.getAttribute('aria-label')).toBe('Demnächst: Vorbestellt')
    expect(chip.getAttribute('href')).toBe('/watchlist/t-1/edit?back=/works/w-1')
  })
})
