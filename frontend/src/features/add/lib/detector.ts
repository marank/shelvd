/**
 * Barcode detector factory: the browser's native BarcodeDetector when it reads our
 * formats, else the ZXing WebAssembly ponyfill. Only imported lazily (from the camera
 * scanner), so neither the ponyfill nor the .wasm end up in the main bundle.
 */

/** Retail barcodes (EAN/UPC), plus Code 128/39: some boxes only carry an article number
 * in one of those (e.g. „Art.-Nr.: 1836540T“ on Nintendo DS games sold in Germany). */
export const FORMATS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'code_39'] as const

export interface Detector {
  detect(source: HTMLVideoElement): Promise<Array<{ rawValue: string }>>
}

interface DetectorClass {
  new (options?: { formats?: string[] }): Detector
  getSupportedFormats?: () => Promise<readonly string[]>
}

async function nativeDetector(): Promise<Detector | null> {
  const Native = (globalThis as { BarcodeDetector?: DetectorClass }).BarcodeDetector
  if (!Native) return null
  try {
    const supported = (await Native.getSupportedFormats?.()) ?? []
    const formats = FORMATS.filter((f) => supported.includes(f))
    // Chrome on desktop exposes the class but supports nothing: fall back then.
    if (!formats.length) return null
    return new Native({ formats })
  } catch {
    return null
  }
}

async function ponyfillDetector(): Promise<Detector> {
  const [{ BarcodeDetector, prepareZXingModule }, { default: wasmUrl }] = await Promise.all([
    import('barcode-detector/ponyfill'),
    import('./zxingWasm'),
  ])
  // Serve the .wasm from our own origin (the CSP forbids the default CDN).
  prepareZXingModule({
    overrides: {
      locateFile: (path: string, prefix: string) =>
        path.endsWith('.wasm') ? wasmUrl : prefix + path,
    },
  })
  return new BarcodeDetector({ formats: [...FORMATS] })
}

/** A detector for retail barcodes (EAN/UPC) and article numbers (Code 128/39). */
export async function createDetector(): Promise<Detector> {
  return (await nativeDetector()) ?? ponyfillDetector()
}
