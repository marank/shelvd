import type { Release } from '@/api/types'

/** A release in a few words: "PS5 · PAL · Special Edition" – what tells it apart from the
 * game's other releases. */
export const releaseLabel = (release: Release) =>
  [
    release.platform.short_name || release.platform.name,
    release.region.toUpperCase(),
    release.edition,
  ]
    .filter(Boolean)
    .join(' · ')
