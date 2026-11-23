import { describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { mockApi, pageText, renderComponent } from '@/test/utils'
import { buildTree, subtreeIds } from '../composables/locationTree'
import LocationsView from '../views/LocationsView.vue'
import { $, $$, exists, LIB, library, location } from './fixtures'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn<(message: string) => void>(), error: vi.fn<(message: string) => void>() },
}))

const url = `/l/${LIB}/locations`
const places = [
  location({ id: 'room', name: 'Living room', kind: 'room', item_count: 1 }),
  location({
    id: 'shelf',
    name: 'Shelf',
    kind: 'shelf',
    parent_id: 'room',
    path: 'Living room › Shelf',
  }),
  location({
    id: 'box',
    name: 'Box A',
    kind: 'box',
    parent_id: 'shelf',
    item_count: 4,
    path: 'Living room › Shelf › Box A',
  }),
  location({ id: 'attic', name: 'Attic', kind: 'unknown' as never }),
]

function api(role: 'owner' | 'editor' | 'viewer', extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries/:id': library(role),
    'GET /api/libraries/:id/locations': places,
    ...extra,
  })
}

const names = () => $$('[data-testid=location-name]').map((n) => n.text())

describe('location tree helpers', () => {
  it('builds a sorted forest and treats orphans as roots', () => {
    const tree = buildTree([...places, location({ id: 'x', name: 'Orphan', parent_id: 'gone' })])
    expect(tree.map((n) => n.location.name)).toEqual(['Attic', 'Living room', 'Orphan'])
    expect(tree[1]!.children[0]!.children[0]!.location.name).toBe('Box A')
  })

  it('collects a subtree', () => {
    expect([...subtreeIds(places, 'room')].sort()).toEqual(['box', 'room', 'shelf'])
    expect([...subtreeIds(places, 'box')]).toEqual(['box'])
  })
})

describe('LocationsView', () => {
  it('shows a read-only collapsible tree to viewers and links to the explorer', async () => {
    api('viewer')
    const { router } = await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(names()).toEqual(['Attic', 'Living room', 'Shelf', 'Box A']))
    expect(pageText()).toContain('4 items')
    expect(exists('[data-testid=add-location]')).toBe(false)
    expect(exists('[data-testid=location-new]')).toBe(false)
    expect(exists('[data-testid=location-edit]')).toBe(false)
    expect(exists('[data-testid=location-delete]')).toBe(false)

    await $('[data-testid=location-room] [data-testid=location-toggle]').trigger('click')
    await vi.waitFor(() => expect(names()).toEqual(['Attic', 'Living room']))
    await $('[data-testid=location-room] [data-testid=location-toggle]').trigger('click')
    await vi.waitFor(() => expect(names()).toHaveLength(4))

    await $('[data-testid=location-box] [data-testid=location-items]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('explorer'))
    expect(router.currentRoute.value.query).toEqual({ g: 'location', p: 'box' })
  })

  it('shows an empty state and load errors', async () => {
    mockApi({ 'GET /api/libraries/:id': library('owner'), 'GET /api/libraries/:id/locations': [] })
    await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=locations-empty]')).toBe(true))
    expect(exists('[data-testid=add-location]')).toBe(true)
  })

  it('shows load errors', async () => {
    mockApi({
      'GET /api/libraries/:id': library('owner'),
      'GET /api/libraries/:id/locations': { status: 500, body: { detail: 'Boom.' } },
    })
    await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(pageText()).toContain('Boom.'))
  })

  it('adds a top-level place and reports errors', async () => {
    let fail = false
    const calls = api('editor', {
      'POST /api/libraries/:id/locations': () =>
        fail
          ? { status: 400, body: { detail: 'Name taken.' } }
          : { status: 201, body: location({ id: 'new', name: 'Garage' }) },
    })
    await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=new-location-name]')).toBe(true))
    await $('[data-testid=new-location-name]').setValue('  ')
    await $('[data-testid=add-location]').trigger('submit')
    expect(calls.some((c) => c.method === 'POST')).toBe(false)

    await $('[data-testid=new-location-name]').setValue('Garage')
    await $('select[data-testid=new-location-kind]').setValue('furniture')
    await $('[data-testid=add-location]').trigger('submit')
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        name: 'Garage',
        kind: 'furniture',
        parent_id: null,
        notes: '',
      }),
    )
    await vi.waitFor(() =>
      expect(($('[data-testid=new-location-name]').element as HTMLInputElement).value).toBe(''),
    )
    expect(toast.success).toHaveBeenCalledWith('Garage added.')

    fail = true
    await $('[data-testid=new-location-name]').setValue('Garage')
    await $('[data-testid=add-location]').trigger('submit')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Name taken.'))
    expect(($('[data-testid=new-location-name]').element as HTMLInputElement).value).toBe('Garage')
  })

  it('adds a child place inline and expands a collapsed parent', async () => {
    const calls = api('owner', {
      'POST /api/libraries/:id/locations': {
        status: 201,
        body: location({ id: 'n', name: 'Box B' }),
      },
    })
    await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(names()).toHaveLength(4))
    // collapse "Shelf", then add inside it
    await $('[data-testid=location-shelf] [data-testid=location-toggle]').trigger('click')
    await $('[data-testid=location-shelf] [data-testid=location-add-child]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=child-form]')).toBe(true))
    // toggling the same button closes the form again
    await $('[data-testid=location-shelf] [data-testid=location-add-child]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=child-form]')).toBe(false))
    await $('[data-testid=location-shelf] [data-testid=location-add-child]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=child-form]')).toBe(true))

    await $('[data-testid=child-form]').trigger('submit') // empty: ignored
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
    await $('[data-testid=child-name]').setValue('Box B')
    await $('[data-testid=child-form]').trigger('submit')
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        name: 'Box B',
        kind: 'box',
        parent_id: 'shelf',
        notes: '',
      }),
    )
    await vi.waitFor(() => expect(exists('[data-testid=child-form]')).toBe(false))
    // the parent was expanded again
    expect(names()).toContain('Box A')

    // cancel button on the inline form
    await $('[data-testid=location-attic] [data-testid=location-add-child]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=child-form]')).toBe(true))
    await $$('[data-testid=child-form] button')
      .find((b) => b.text() === 'Cancel')!
      .trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=child-form]')).toBe(false))
  })

  it('adds a child below an expanded parent', async () => {
    api('owner', {
      'POST /api/libraries/:id/locations': { status: 201, body: location({ id: 'n', name: 'X' }) },
    })
    await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(names()).toHaveLength(4))
    await $('[data-testid=location-room] [data-testid=location-add-child]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=child-name]')).toBe(true))
    await $('[data-testid=child-name]').setValue('X')
    await $('[data-testid=child-form]').trigger('submit')
    await vi.waitFor(() => expect(exists('[data-testid=child-form]')).toBe(false))
    expect(names()).toContain('Shelf')
  })

  it('links to the edit and new pages, including "more" from the inline form', async () => {
    api('editor')
    const { router } = await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(names()).toHaveLength(4))
    expect($('[data-testid=location-new]').attributes('href')).toBe(`/l/${LIB}/locations/new`)

    await $('[data-testid=location-shelf] [data-testid=location-add-child]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=child-more]')).toBe(true))
    expect($('[data-testid=child-more]').attributes('href')).toBe(
      `/l/${LIB}/locations/new?parent=shelf`,
    )

    await $('[data-testid=location-shelf] [data-testid=location-edit]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('location-edit'))
    expect(router.currentRoute.value.params).toEqual({ libraryId: LIB, locationId: 'shelf' })
  })

  it('deletes a place after explaining what happens', async () => {
    let fail = true
    const calls = api('owner', {
      'DELETE /api/libraries/:id/locations/:loc': () =>
        fail ? { status: 404, body: { detail: 'Not found.' } } : { status: 204 },
    })
    await renderComponent(LocationsView, { url })
    await vi.waitFor(() => expect(names()).toHaveLength(4))
    await $('[data-testid=location-room] [data-testid=location-delete]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    expect(pageText()).toContain('Delete Living room?')
    expect(pageText()).toContain('All places inside it are deleted too')
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect($('[data-testid=confirm-error]').text()).toBe('Not found.'))
    fail = false
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(false))
    expect(calls.filter((c) => c.method === 'DELETE').at(-1)?.path).toBe(
      `/api/libraries/${LIB}/locations/room`,
    )
    expect(toast.success).toHaveBeenCalledWith('Living room deleted.')
  })
})
