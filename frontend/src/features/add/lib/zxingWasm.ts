// The ZXing reader binary, emitted as an asset of our own build (hashed URL, same origin):
// the CSP allows no CDN. Keep zxing-wasm's version equal to the one barcode-detector uses.
import wasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url'

export default wasmUrl
