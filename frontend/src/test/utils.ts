/**
 * Test helpers: mount a component (or the whole app at a URL) with the real router,
 * i18n, Pinia and TanStack Query, against a fake /api answered by `mockApi`.
 */
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount, type ComponentMountingOptions } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { expect, vi } from 'vitest'
import { defineComponent, h, type Component } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import App from '@/App.vue'
import type { User } from '@/api/types'
import { i18n } from '@/i18n'
import { appRoutes, installGuard } from '@/router'
import { useAuthStore } from '@/stores/auth'

const mounted: { unmount: () => void }[] = []

/** Unmount everything mounted by the helpers (called from test/setup.ts after each test). */
export function cleanup(): void {
  while (mounted.length) mounted.pop()?.unmount()
}

export const testUser: User = {
  id: '00000000-0000-0000-0000-000000000001',
  username: 'alice',
  email: 'alice@example.com',
  // The admin (most tests use catalog actions); viewer tests override this.
  is_staff: true,
  can_contribute: true,
}

/** Neither admin nor editor anywhere: may not touch the catalog. */
export const plainUser: User = { ...testUser, is_staff: false, can_contribute: false }

export interface ApiCall {
  method: string
  path: string
  query: URLSearchParams
  body: unknown
}

/** A response body, or `{status, body}` (see isReply). */
type Reply = unknown
type Handler = (call: ApiCall, params: Record<string, string>) => Reply

/** `{status: 201, body}` or `{status: 204}` — not an API object that happens to have a
 * `status` field (items do). */
function isReply(value: unknown): value is { status?: number; body?: unknown } {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const keys = Object.keys(value)
  return (
    keys.length > 0 &&
    keys.every((k) => k === 'status' || k === 'body') &&
    typeof (value as { status?: unknown }).status === 'number'
  )
}

/**
 * Fake the backend. Keys are "METHOD /api/path/:param"; values are a response body,
 * `{status, body}`, or a function returning either. Unmatched requests answer 404.
 * Returns the list of calls for assertions.
 */
export function mockApi(routes: Record<string, unknown>): ApiCall[] {
  const calls: ApiCall[] = []
  const table = Object.entries(routes).map(([key, handler]) => {
    const [method, pattern] = key.split(' ') as [string, string]
    const names: string[] = []
    const regex = new RegExp(
      '^' +
        pattern.replace(/:([a-zA-Z_]+)/g, (_, name: string) => (names.push(name), '([^/]+)')) +
        '$',
    )
    return { method, regex, names, handler }
  })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = input instanceof Request ? input : new Request(String(input), init)
      const url = new URL(request.url, 'http://localhost')
      const text = request.method === 'GET' ? '' : await request.text()
      let body: unknown = text
      try {
        body = text ? JSON.parse(text) : undefined
      } catch {
        // multipart or plain text: keep the raw text
      }
      const call: ApiCall = {
        method: request.method,
        path: url.pathname,
        query: url.searchParams,
        body,
      }
      calls.push(call)
      for (const route of table) {
        const match = route.method === request.method && route.regex.exec(url.pathname)
        if (!match) continue
        const params = Object.fromEntries(route.names.map((n, i) => [n, match[i + 1] ?? '']))
        const result =
          typeof route.handler === 'function'
            ? await (route.handler as Handler)(call, params)
            : route.handler
        const reply = isReply(result) ? result : { status: 200, body: result }
        const status = reply.status ?? 200
        return new Response(status === 204 ? null : JSON.stringify(reply.body ?? null), {
          status,
          headers: { 'content-type': 'application/json' },
        })
      }
      return new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 })
    }),
  )
  return calls
}

interface Setup {
  user?: User | null
  locale?: 'de' | 'en'
}

function setup({ user = testUser, locale = 'en' }: Setup) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = user
  i18n.global.locale.value = locale
  const router = createRouter({ history: createMemoryHistory(), routes: appRoutes() })
  installGuard(router)
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
  })
  const plugins = [pinia, i18n, router, [VueQueryPlugin, { queryClient }]] as const
  return { pinia, router, queryClient, plugins }
}

/** Mount the whole app (layouts included) at a URL. */
export async function renderApp(url: string, options: Setup = {}) {
  const ctx = setup(options)
  await ctx.router.push(url)
  await ctx.router.isReady()
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [...ctx.plugins] as never },
  })
  mounted.push(wrapper)
  await settle()
  return { ...ctx, wrapper }
}

/** Mount one component inside a router (at `url`) with all plugins. */
export async function renderComponent<C extends Component>(
  component: C,
  options: Setup & { url?: string; props?: ComponentMountingOptions<C>['props'] } = {},
) {
  const ctx = setup(options)
  await ctx.router.push(options.url ?? '/')
  await ctx.router.isReady()
  const Host = defineComponent({
    render: () => [
      h(component, options.props as Record<string, unknown>),
      h(RouterView, { name: 'none' }),
    ],
  })
  const wrapper = mount(Host, {
    attachTo: document.body,
    global: { plugins: [...ctx.plugins] as never },
  })
  mounted.push(wrapper)
  await settle()
  return { ...ctx, wrapper }
}

/** Let fetches, queries and re-renders finish. */
export async function settle(rounds = 4): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await flushPromises()
    await new Promise((resolve) => setTimeout(resolve, 0))
  }
}

/** Text of the whole document (dialogs and sheets are teleported to body). */
export function pageText(): string {
  return document.body.textContent
}

/** Open a dropdown menu by its trigger's test id (reka opens menus on Enter). */
export async function openMenu(testId: string): Promise<void> {
  document
    .querySelector(`[data-testid="${testId}"]`)!
    .dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  await settle()
}

/** Types into a TermPicker/EditionInput, waits for the wanted suggestion and takes it
 * with Enter. */
export async function pickTerm(selector: string, text: string, option: string): Promise<void> {
  const input = document.querySelector(selector) as HTMLInputElement
  input.dispatchEvent(new Event('focus'))
  input.value = text
  input.dispatchEvent(new Event('input'))
  await settle()
  await vi.waitFor(() => {
    const active = document.querySelector(`${selector}-suggestions [aria-selected="true"]`)
    expect(active?.textContent).toContain(option)
  })
  input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  await settle()
}

/** The chips of a TermPicker (by its input's selector, `#id`). */
export const pickerChips = (selector: string): string[] =>
  [
    ...document.querySelectorAll(
      `[data-testid="${selector.slice(1)}-picker"] [data-testid="picked"]`,
    ),
  ].map((c) => c.textContent.trim())
