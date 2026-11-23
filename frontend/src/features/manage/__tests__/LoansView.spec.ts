import { describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { mockApi, pageText, renderComponent, settle } from '@/test/utils'
import { todayIso } from '../composables/format'
import LoansView from '../views/LoansView.vue'
import { $, $$, exists, LIB, library, loan } from './fixtures'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn<(message: string) => void>(), error: vi.fn<(message: string) => void>() },
}))

const url = `/l/${LIB}/loans`
const open = [
  loan({ id: 'l1', item_title: 'Mario Kart 8', overdue: true }),
  loan({ id: 'l2', item_id: 'item-2', item_title: 'Zelda', due_on: null, platform: 'NDS' }),
]
const returned = [loan({ id: 'l3', item_title: 'Metroid', returned_on: '2026-10-20' })]

function api(role: 'owner' | 'editor' | 'viewer', extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries/:id': library(role),
    'GET /api/catalog/platforms': [
      {
        id: 'x',
        name: 'Nintendo Switch',
        short_name: 'Switch',
        slug: 'switch',
        manufacturer: 'Nintendo',
        media_type: 'cartridge',
        release_year: 2017,
      },
    ],
    'GET /api/libraries/:id/loans': ({ query }: { query: URLSearchParams }) =>
      query.get('open') === 'true' ? open : returned,
    ...extra,
  })
}

describe('LoansView', () => {
  it('lists open loans with summary, overdue highlight and opens the item', async () => {
    api('viewer')
    const { router } = await renderComponent(LoansView, { url })
    await vi.waitFor(() => expect($$('[data-testid=loan-row]')).toHaveLength(2))
    expect($('[data-testid=loan-summary]').text()).toMatch(/2\s*open\s*·\s*1\s*overdue/)
    expect(pageText()).toContain('Lent to Carol')
    expect(pageText()).toContain('Overdue')
    expect($$('[data-testid=loan-due]')[0]!.classes()).toContain('text-destructive')
    expect($$('[data-testid=loan-due]')[1]!.text()).toBe('—')
    // viewers can't change anything
    expect(exists('[data-testid=loan-return]')).toBe(false)
    expect(exists('[data-testid=loan-delete]')).toBe(false)

    await $$('[data-testid=loan-row]')[1]!.trigger('keydown', { key: 'Enter' })
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('explorer'))
    expect(router.currentRoute.value.query.item).toBe('item-2')
  })

  it('shows the history tab and an empty state', async () => {
    mockApi({
      'GET /api/libraries/:id': library('owner'),
      'GET /api/libraries/:id/loans': ({ query }: { query: URLSearchParams }) =>
        query.get('open') === 'true' ? [] : returned,
    })
    await renderComponent(LoansView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=loans-empty]')).toBe(true))
    expect(pageText()).toContain('Nothing is lent out right now.')

    await $('[data-testid=tab-history]').trigger('mousedown', { button: 0 })
    await vi.waitFor(() => expect($$('[data-testid=loan-row]')).toHaveLength(1))
    expect(pageText()).toContain('Metroid')
    // already returned: no return button, but delete is there
    expect(exists('[data-testid=loan-return]')).toBe(false)
    expect(exists('[data-testid=loan-delete]')).toBe(true)
  })

  it('shows an empty history', async () => {
    mockApi({ 'GET /api/libraries/:id': library('owner'), 'GET /api/libraries/:id/loans': [] })
    await renderComponent(LoansView, { url })
    await $('[data-testid=tab-history]').trigger('mousedown', { button: 0 })
    await vi.waitFor(() => expect(pageText()).toContain('No returned loans yet.'))
  })

  it('shows load errors', async () => {
    mockApi({
      'GET /api/libraries/:id': library('owner'),
      'GET /api/libraries/:id/loans': { status: 403, body: { detail: 'No access.' } },
    })
    await renderComponent(LoansView, { url })
    await vi.waitFor(() => expect(pageText()).toContain('No access.'))
  })

  it('lets editors mark a loan returned with a date', async () => {
    const calls = api('editor', {
      'POST /api/libraries/:id/loans/:loan/return': loan({ id: 'l1', returned_on: '2026-10-30' }),
    })
    const { router } = await renderComponent(LoansView, { url })
    await vi.waitFor(() => expect($$('[data-testid=loan-return]')).toHaveLength(2))
    await $$('[data-testid=loan-return]')[0]!.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=return-form]')).toBe(true))
    expect(exists('[role=dialog]')).toBe(false)
    // the form replaces the button of that row only
    expect($$('[data-testid=loan-return]')).toHaveLength(1)
    expect(($('[data-testid=return-date]').element as HTMLInputElement).value).toBe(todayIso())
    await $('[data-testid=return-date]').setValue('2026-10-30')
    await $('[data-testid=return-form]').trigger('submit')
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ returned_on: '2026-10-30' }),
    )
    expect(calls.find((c) => c.method === 'POST')?.path).toBe(
      `/api/libraries/${LIB}/loans/l1/return`,
    )
    await vi.waitFor(() => expect(exists('[data-testid=return-form]')).toBe(false))
    expect(toast.success).toHaveBeenCalled()
    // the click on the action did not open the item
    expect(router.currentRoute.value.name).toBe('loans')
    // loans were refetched
    expect(
      calls.filter((c) => c.path.endsWith('/loans') && c.method === 'GET').length,
    ).toBeGreaterThan(2)
  })

  it('shows the error when returning fails and can cancel', async () => {
    const calls = api('owner', {
      'POST /api/libraries/:id/loans/:loan/return': {
        status: 400,
        body: { detail: 'Date before lending.' },
      },
    })
    await renderComponent(LoansView, { url })
    await vi.waitFor(() => expect($$('[data-testid=loan-return]')).toHaveLength(2))
    await $$('[data-testid=loan-return]')[0]!.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=return-confirm]')).toBe(true))
    await $('[data-testid=return-confirm]').trigger('click')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Date before lending.'))
    // the inline form stays open to correct the date
    expect(exists('[data-testid=return-form]')).toBe(true)
    const cancel = $$('[data-testid=return-form] button').find((b) => b.text() === 'Cancel')!
    await cancel.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=return-form]')).toBe(false))
    expect($$('[data-testid=loan-return]')).toHaveLength(2)

    // an emptied date field lets the server use today
    await $$('[data-testid=loan-return]')[1]!.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=return-form]')).toBe(true))
    await $('[data-testid=return-date]').setValue('')
    await $('[data-testid=return-form]').trigger('submit')
    await vi.waitFor(() =>
      expect(calls.filter((c) => c.method === 'POST').at(-1)?.body).toEqual({ returned_on: null }),
    )
  })

  it('deletes a loan entry after confirmation and shows errors', async () => {
    let fail = true
    const calls = api('owner', {
      'DELETE /api/libraries/:id/loans/:loan': () =>
        fail ? { status: 409, body: { detail: 'Locked.' } } : { status: 204 },
    })
    await renderComponent(LoansView, { url })
    await vi.waitFor(() => expect($$('[data-testid=loan-delete]')).toHaveLength(2))
    await $$('[data-testid=loan-delete]')[1]!.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    expect(pageText()).toContain('The entry for Zelda disappears')
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect($('[data-testid=confirm-error]').text()).toBe('Locked.'))
    fail = false
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(false))
    expect(calls.filter((c) => c.method === 'DELETE').map((c) => c.path)).toEqual([
      `/api/libraries/${LIB}/loans/l2`,
      `/api/libraries/${LIB}/loans/l2`,
    ])
    await settle()
  })
})
