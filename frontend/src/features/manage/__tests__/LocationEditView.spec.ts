import { describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { mockApi, pageText, renderComponent } from '@/test/utils'
import LocationEditView from '../views/LocationEditView.vue'
import { $, $$, exists, LIB, library, location } from './fixtures'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn<(message: string) => void>(), error: vi.fn<(message: string) => void>() },
}))

const places = [
  location({ id: 'room', name: 'Living room', kind: 'room', item_count: 1 }),
  location({
    id: 'shelf',
    name: 'Shelf',
    kind: 'shelf',
    parent_id: 'room',
    notes: 'Billy',
    item_count: 7,
    path: 'Living room › Shelf',
  }),
  location({
    id: 'box',
    name: 'Box A',
    kind: 'box',
    parent_id: 'shelf',
    path: 'Living room › Shelf › Box A',
  }),
  location({ id: 'attic', name: 'Attic', kind: 'other', path: '' }),
]

function api(role: 'owner' | 'editor' | 'viewer', extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries/:id': library(role),
    'GET /api/libraries/:id/locations': places,
    ...extra,
  })
}

const value = (selector: string) => ($(selector).element as HTMLInputElement).value
const checkedKind = () =>
  document.body.querySelector<HTMLInputElement>('input[name=location-kind]:checked')?.value

describe('LocationEditView', () => {
  it('edits a place: name, kind cards, parent without its own subtree, notes', async () => {
    let fail = true
    const calls = api('editor', {
      'PATCH /api/libraries/:id/locations/:loc': () =>
        fail ? { status: 400, body: { detail: 'A place cannot be inside itself.' } } : places[1],
    })
    const { router } = await renderComponent(LocationEditView, {
      url: `/l/${LIB}/locations/shelf/edit`,
    })
    await vi.waitFor(() => expect(exists('#location-name')).toBe(true))
    expect(value('#location-name')).toBe('Shelf')
    expect(value('#location-notes')).toBe('Billy')
    expect(checkedKind()).toBe('shelf')
    expect(pageText()).toContain('Edit place')
    expect($('[data-testid=location-path]').text()).toBe('Living room › Shelf')
    expect($('[data-testid=location-count]').text()).toBe('7 items')
    expect($('[data-testid=location-items]').attributes('href')).toBe(
      `/l/${LIB}?g=location&p=shelf`,
    )
    // all five kinds as radio cards
    expect($$('input[name=location-kind]')).toHaveLength(5)
    const parents = $$('#location-parent option').map((o) => o.attributes('value'))
    expect(parents).toEqual(['', 'attic', 'room']) // not itself, not Box A

    await $('#location-name').setValue('Big shelf')
    await $('[data-testid=kind-furniture] input').setValue(true)
    expect(checkedKind()).toBe('furniture')
    await $('#location-parent').setValue('attic')
    await $('#location-notes').setValue('IKEA')
    await $('form').trigger('submit')
    await vi.waitFor(() =>
      expect($('[data-testid=edit-error]').text()).toBe('A place cannot be inside itself.'),
    )
    fail = false
    await $('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('locations'))
    const patch = calls.filter((c) => c.method === 'PATCH').at(-1)!
    expect(patch.path).toBe(`/api/libraries/${LIB}/locations/shelf`)
    expect(patch.body).toEqual({
      name: 'Big shelf',
      kind: 'furniture',
      parent_id: 'attic',
      notes: 'IKEA',
    })
    expect(toast.success).toHaveBeenCalledWith('Place saved.')
  })

  it('requires a name and sends null for the top level', async () => {
    const calls = api('owner', { 'PATCH /api/libraries/:id/locations/:loc': places[0] })
    await renderComponent(LocationEditView, { url: `/l/${LIB}/locations/room/edit` })
    await vi.waitFor(() => expect(value('#location-name')).toBe('Living room'))
    // a place without path shows its name
    await $('#location-name').setValue('  ')
    await $('form').trigger('submit')
    await vi.waitFor(() =>
      expect($('[data-testid=edit-error]').text()).toBe('Please enter a name.'),
    )
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
    await $('#location-name').setValue('Lounge')
    await $('form').trigger('submit')
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')?.body).toMatchObject({ parent_id: null }),
    )
  })

  it('reloads the form when switching to another place', async () => {
    api('owner')
    const { router } = await renderComponent(LocationEditView, {
      url: `/l/${LIB}/locations/attic/edit`,
    })
    await vi.waitFor(() => expect(value('#location-name')).toBe('Attic'))
    expect($('[data-testid=location-path]').text()).toBe('Attic')
    await router.push(`/l/${LIB}/locations/box/edit`)
    await vi.waitFor(() => expect(value('#location-name')).toBe('Box A'))
    expect(checkedKind()).toBe('box')
  })

  it('creates a place inside a preset parent', async () => {
    const calls = api('editor', {
      'POST /api/libraries/:id/locations': {
        status: 201,
        body: location({ id: 'new', name: 'Box B' }),
      },
    })
    const { router } = await renderComponent(LocationEditView, {
      url: `/l/${LIB}/locations/new?parent=shelf`,
    })
    await vi.waitFor(() => expect(value('#location-parent')).toBe('shelf'))
    expect(pageText()).toContain('New place')
    expect(checkedKind()).toBe('box')
    // all places are possible parents of a new one; no info section, no delete
    expect($$('#location-parent option')).toHaveLength(5)
    expect(exists('[data-testid=location-path]')).toBe(false)
    expect(exists('[data-testid=location-delete]')).toBe(false)
    expect($('[data-testid=edit-save]').text()).toBe('Create')
    await $('#location-name').setValue('Box B')
    await $('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('locations'))
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      name: 'Box B',
      kind: 'box',
      parent_id: 'shelf',
      notes: '',
    })
    expect(toast.success).toHaveBeenCalledWith('Box B added.')
  })

  it('creates a top-level room when the parent is unknown and shows errors', async () => {
    const calls = api('owner', {
      'POST /api/libraries/:id/locations': { status: 400, body: { detail: 'Name taken.' } },
    })
    await renderComponent(LocationEditView, { url: `/l/${LIB}/locations/new?parent=gone` })
    await vi.waitFor(() => expect(exists('#location-parent')).toBe(true))
    expect(value('#location-parent')).toBe('')
    expect(checkedKind()).toBe('room')
    await $('#location-name').setValue('Garage')
    await $('form').trigger('submit')
    await vi.waitFor(() => expect($('[data-testid=edit-error]').text()).toBe('Name taken.'))
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({ parent_id: null })
  })

  it('shows unknown places and load errors', async () => {
    api('owner')
    await renderComponent(LocationEditView, { url: `/l/${LIB}/locations/nope/edit` })
    await vi.waitFor(() =>
      expect($('[data-testid=location-load-error]').text()).toBe(
        "This place doesn't exist (anymore).",
      ),
    )
  })

  it('shows a failing location request', async () => {
    mockApi({
      'GET /api/libraries/:id': library('owner'),
      'GET /api/libraries/:id/locations': { status: 500, body: { detail: 'Boom.' } },
    })
    await renderComponent(LocationEditView, { url: `/l/${LIB}/locations/room/edit` })
    await vi.waitFor(() => expect($('[data-testid=location-load-error]').text()).toBe('Boom.'))
  })

  it('does not let viewers save or delete', async () => {
    const calls = api('viewer')
    await renderComponent(LocationEditView, { url: `/l/${LIB}/locations/room/edit` })
    await vi.waitFor(() => expect(value('#location-name')).toBe('Living room'))
    expect(exists('[data-testid=location-delete]')).toBe(false)
    await $('form').trigger('submit')
    await vi.waitFor(() =>
      expect($('[data-testid=edit-error]').text()).toBe('You can only view this library.'),
    )
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
  })

  it('deletes the place after confirmation', async () => {
    let fail = true
    const calls = api('owner', {
      'DELETE /api/libraries/:id/locations/:loc': () =>
        fail ? { status: 404, body: { detail: 'Not found.' } } : { status: 204 },
    })
    const { router } = await renderComponent(LocationEditView, {
      url: `/l/${LIB}/locations/room/edit`,
    })
    await vi.waitFor(() => expect(exists('[data-testid=location-delete]')).toBe(true))
    await $('[data-testid=location-delete]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    expect(pageText()).toContain('Delete Living room?')
    // the delete button did not submit the form
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect($('[data-testid=confirm-error]').text()).toBe('Not found.'))
    fail = false
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('locations'))
    expect(calls.filter((c) => c.method === 'DELETE').at(-1)?.path).toBe(
      `/api/libraries/${LIB}/locations/room`,
    )
    expect(toast.success).toHaveBeenCalledWith('Living room deleted.')
  })
})
