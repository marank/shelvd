import type { Item } from '@/api/types'

/** What tells copies of one game apart: "Switch · PAL · Steelbook". */
export function copyLabel(copy: Item): string {
  const release = copy.release
  return [
    release.platform.short_name || release.platform.name,
    release.region.toUpperCase(),
    release.edition,
  ]
    .filter(Boolean)
    .join(' · ')
}
