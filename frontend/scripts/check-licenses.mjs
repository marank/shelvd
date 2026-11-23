// Fail if a production dependency's license can't be combined with shelvd's AGPL-3.0.
// GPL-3.0, AGPL-3.0, LGPL and GPL "v2 or later" are fine; SSPL and GPL v2 *only* aren't.
// Reads `pnpm licenses list --prod --json` (keys are SPDX expressions).
import { execFileSync } from 'node:child_process'

const SSPL = /SSPL|Server Side Public License/i
// "GPL-2.0", "GPL-2.0-only", "GPLv2" – but not "GPL-2.0-or-later", "GPL-2.0+" or any LGPL.
const GPL2_ONLY = /(?<![A-Za-z])GPL-?v?2(?:\.0)?(?![\d.]*\+|[\d.]*-or-later)/i
// Packages whose metadata is wrong or ambiguous (e.g. "MIT OR GPL-2.0": we take MIT),
// after checking them by hand: { 'package-name': 'reason' }
const ALLOW = {}

const incompatible = (license) => SSPL.test(license) || GPL2_ONLY.test(license)

const byLicense = JSON.parse(
  execFileSync('pnpm', ['licenses', 'list', '--prod', '--json'], { encoding: 'utf8' }),
)
const bad = []
for (const [license, packages] of Object.entries(byLicense)) {
  if (!incompatible(license)) continue
  for (const pkg of packages) {
    if (!(pkg.name in ALLOW)) bad.push(`${pkg.name} ${pkg.versions?.join(', ') ?? ''}: ${license}`)
  }
}
for (const line of bad) console.log(`license not compatible with AGPL-3.0: ${line}`)
if (!bad.length) console.log('licenses ok')
process.exit(bad.length ? 1 : 0)
