import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'
import { getCsrfToken } from './csrf'

const SAFE = new Set(['GET', 'HEAD', 'OPTIONS'])

let language = 'de'
let onUnauthorized: (() => void) | undefined

/** Backend messages follow the UI language. */
export function setApiLanguage(value: string): void {
  language = value
}

/** Called on 401 (session expired); wired to the auth store and router in main.ts. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

export const csrfMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getCsrfToken() // re-read every time: Django rotates it on login
    if (!SAFE.has(request.method) && token) request.headers.set('X-CSRFToken', token)
    request.headers.set('Accept-Language', language)
    return request
  },
}

export const unauthorizedMiddleware: Middleware = {
  onResponse({ request, response }) {
    // /api/auth/me answering 401 during boot just means "not logged in".
    if (response.status === 401 && !request.url.endsWith('/api/auth/me')) onUnauthorized?.()
    return response
  },
}

export const api = createClient<paths>({
  // Same origin; absolute so Request objects also work outside a browser (tests).
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- no `location` when this module loads outside a browser
  baseUrl: globalThis.location?.origin ?? '',
  credentials: 'same-origin',
  // Resolved per request, so tests can replace globalThis.fetch.
  fetch: (request) => globalThis.fetch(request),
})
api.use(csrfMiddleware, unauthorizedMiddleware)
