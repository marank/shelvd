import { afterEach, describe, expect, it, vi } from 'vitest'
import { createDetector, FORMATS } from '../lib/detector'

const ponyfill = vi.hoisted(() => {
  const instances: unknown[] = []
  class BarcodeDetector {
    constructor(readonly options: unknown) {
      instances.push(this)
    }
    detect = () => Promise.resolve([])
  }
  return {
    BarcodeDetector,
    prepareZXingModule:
      vi.fn<
        (options: { overrides: { locateFile: (path: string, prefix: string) => string } }) => void
      >(),
    instances,
  }
})

vi.mock('barcode-detector/ponyfill', () => ponyfill)
vi.mock('../lib/zxingWasm', () => ({ default: '/assets/zxing_reader-abc.wasm' }))

function nativeClass(getSupportedFormats?: () => Promise<string[]>) {
  return class Native {
    static getSupportedFormats = getSupportedFormats
    constructor(readonly options: { formats: string[] }) {}
    detect = () => Promise.resolve([])
  }
}

afterEach(() => {
  ponyfill.prepareZXingModule.mockClear()
  ponyfill.instances.length = 0
})

describe('createDetector', () => {
  it('uses the native BarcodeDetector with the formats it supports', async () => {
    vi.stubGlobal(
      'BarcodeDetector',
      nativeClass(() => Promise.resolve(['qr_code', 'ean_13', 'upc_a'])),
    )
    const detector = (await createDetector()) as unknown as { options: { formats: string[] } }
    expect(detector.options.formats).toEqual(['ean_13', 'upc_a'])
    expect(ponyfill.prepareZXingModule).not.toHaveBeenCalled()
  })

  it('falls back to the ponyfill with a same-origin .wasm', async () => {
    const detector = (await createDetector()) as unknown as { options: { formats: string[] } }
    expect(detector.options).toEqual({ formats: [...FORMATS] })
    const { overrides } = ponyfill.prepareZXingModule.mock.calls[0]![0]
    expect(overrides.locateFile('zxing_reader.wasm', 'https://cdn/')).toBe(
      '/assets/zxing_reader-abc.wasm',
    )
    expect(overrides.locateFile('other.js', '/x/')).toBe('/x/other.js')
  })

  it('falls back when the native one supports none of our formats', async () => {
    vi.stubGlobal(
      'BarcodeDetector',
      nativeClass(() => Promise.resolve(['qr_code'])),
    )
    await createDetector()
    expect(ponyfill.instances).toHaveLength(1)
  })

  it('falls back when the native one has no format list or fails', async () => {
    vi.stubGlobal('BarcodeDetector', nativeClass())
    await createDetector()
    vi.stubGlobal(
      'BarcodeDetector',
      nativeClass(() => Promise.reject(new Error('nope'))),
    )
    await createDetector()
    expect(ponyfill.instances).toHaveLength(2)
  })
})
