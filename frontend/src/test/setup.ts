import { afterEach, vi } from 'vitest'
import { LOCALES, loadLocale } from '@/i18n'
import { cleanup } from './utils'

// Tests switch the language synchronously, so both are loaded up front.
await Promise.all(LOCALES.map(loadLocale))

// jsdom lacks a few browser APIs that Reka UI / VueUse touch.
// jsdom declares some of them but leaves them undefined, hence Partial<…>.
if (!(window as Partial<Window>).matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!(globalThis as Partial<typeof globalThis>).ResizeObserver)
  globalThis.ResizeObserver = ResizeObserverStub
if (!(globalThis as Partial<typeof globalThis>).IntersectionObserver)
  globalThis.IntersectionObserver = ResizeObserverStub as unknown as typeof IntersectionObserver
/** Adds what jsdom lacks; leaves what it has. */
function stubElementMethod(name: keyof Element, value: () => unknown) {
  if (!(Element.prototype as Partial<Element>)[name])
    Object.defineProperty(Element.prototype, name, { value, configurable: true, writable: true })
}
stubElementMethod('scrollIntoView', () => {})
stubElementMethod('hasPointerCapture', () => false)
stubElementMethod('releasePointerCapture', () => {})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
  document.cookie.split('; ').forEach((c) => {
    document.cookie = `${c.split('=')[0]}=; expires=Thu, 01 Jan 1970 00:00:00 GMT`
  })
  try {
    localStorage.clear()
  } catch {
    // ignore
  }
})
