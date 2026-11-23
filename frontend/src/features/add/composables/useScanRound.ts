import { computed, ref, toValue, type MaybeRefOrGetter, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApiError } from '@/api/errors'
import type { BarcodeLookup, Candidate, Item, Release, Tracking } from '@/api/types'
import type { AddDestination } from '@/stores/ui'
import { useOwned } from '@/features/library/composables/useOwned'
import { useItemMutations } from '@/features/items/composables/useItem'
import { useCreateTracking, useDeleteTracking } from '@/features/watchlist/composables/useWatchlist'
import {
  attachBarcode,
  isRegion,
  lookupBarcode,
  useCreateItem,
  useImportCandidate,
} from './useAddApi'
import { toItemIn, type ItemDetails } from './useItemDetails'
import { firstText } from '@/lib/utils'

/**
 * looking – asking the server; review – options to pick from; unknown – nothing found;
 * saving – being added; added/tracked – done; failed – the lookup failed.
 */
export type EntryState =
  'looking' | 'review' | 'unknown' | 'saving' | 'added' | 'tracked' | 'failed'

export type Choice =
  { kind: 'release'; release: Release } | { kind: 'candidate'; candidate: Candidate }

/** One scanned code (or one game picked in the search) of this round. */
export interface ScanEntry {
  id: number
  /** Empty for a game picked in the search without a scan. */
  code: string
  state: EntryState
  lookup: BarcodeLookup | null
  /** Picked in the search; replaces the lookup's options. */
  picked: Choice | null
  release: Release | null
  item: Item | null
  tracking: Tracking | null
  error: string
  /** The one known release is in the library already (or was added this round): not
   * added automatically, the sheet asks for another copy instead. */
  duplicateOf: string | null
}

/** A code still in view is reported again and again; ignore it until it was gone this long. */
const SAME_CODE_MS = 4000

function choiceTitle(choice: Choice): string {
  return choice.kind === 'release' ? choice.release.title : choice.candidate.title
}

export function choicesOf(entry: ScanEntry): Choice[] {
  if (entry.picked) return [entry.picked]
  const lookup = entry.lookup
  if (!lookup) return []
  return lookup.known.map((release): Choice => ({ kind: 'release', release }))
}

export function entryTitle(entry: ScanEntry): string {
  if (entry.release) return entry.release.title
  const first = choicesOf(entry)[0]
  return first ? choiceTitle(first) : ''
}

/**
 * A scanning round on the phone: every code becomes an entry of the queue; a code we
 * know exactly one game for is added right away (if wanted), everything else waits for a
 * decision in the sheet. All copies get the round's details.
 */
export function useScanRound(options: {
  libraryId: MaybeRefOrGetter<string>
  details: Ref<ItemDetails>
  autoAdd: MaybeRefOrGetter<boolean>
  destination: MaybeRefOrGetter<AddDestination | null>
}) {
  const { t } = useI18n()
  const entries = ref<ScanEntry[]>([])
  /** The entry the sheet shows. */
  const activeId = ref<number | null>(null)
  const active = computed(() => entries.value.find((e) => e.id === activeId.value) ?? null)
  const done = computed(
    () => entries.value.filter((e) => e.state === 'added' || e.state === 'tracked').length,
  )
  const creator = useCreateItem(options.libraryId)
  const remover = useItemMutations(options.libraryId).remove
  const importer = useImportCandidate()
  const tracker = useCreateTracking()
  const untracker = useDeleteTracking()
  const owned = useOwned(options.libraryId)
  const seen = new Map<string, number>()
  let nextId = 1

  /** Owned in the library, or added earlier this round (the list may not have caught up). */
  async function alreadyHave(entry: ScanEntry, release: Release): Promise<boolean> {
    const added = entries.value.some(
      (e) => e.id !== entry.id && e.state === 'added' && e.release?.id === release.id,
    )
    if (added) return true
    if (owned.isPending.value && toValue(options.libraryId)) await owned.suspense().catch(() => {})
    return (owned.data.value?.releases.get(release.id) ?? 0) > 0
  }

  const message = (e: unknown) => (e instanceof ApiError ? e.message : t('errors.generic'))

  function destinationFor(release: Release): AddDestination {
    return toValue(options.destination) ?? (release.is_released ? 'library' : 'track')
  }

  function create(code: string, state: EntryState): ScanEntry {
    entries.value.unshift({
      id: nextId++,
      code,
      state,
      lookup: null,
      picked: null,
      release: null,
      item: null,
      tracking: null,
      error: '',
      duplicateOf: null,
    })
    // The reactive proxy, so later changes re-render.
    return entries.value[0]!
  }

  /** Show the entry in the sheet unless another one is open already. */
  function offer(entry: ScanEntry) {
    activeId.value ??= entry.id
  }

  async function look(entry: ScanEntry) {
    entry.state = 'looking'
    entry.error = ''
    try {
      entry.lookup = await lookupBarcode(entry.code)
    } catch (e) {
      entry.state = 'failed'
      entry.error = message(e)
      offer(entry)
      return
    }
    const choices = choicesOf(entry)
    const only = choices.length === 1 ? entry.lookup.known[0] : null
    if (only && toValue(options.autoAdd) && destinationFor(only) === 'library') {
      if (!(await alreadyHave(entry, only))) {
        await add(entry, { kind: 'release', release: only })
        return
      }
      entry.duplicateOf = only.id
    }
    entry.state = choices.length ? 'review' : 'unknown'
    offer(entry)
  }

  /** A code from the camera or typed in. */
  function scan(raw: string) {
    const code = raw.replace(/\s+/g, '')
    if (!code) return
    const now = Date.now()
    const last = seen.get(code)
    seen.set(code, now)
    if (last !== undefined && now - last < SAME_CODE_MS) return
    void look(create(code, 'looking'))
  }

  /** The catalog release for a choice: imports a candidate, remembers the code. */
  async function resolve(entry: ScanEntry, choice: Choice, platformId?: string) {
    if (choice.kind === 'candidate') {
      const c = choice.candidate
      return importer.mutateAsync({
        provider: c.provider,
        external_id: c.external_id,
        platform_id: firstText(platformId, c.platform_id) ?? '',
        region: isRegion(c.region) ? c.region : 'pal',
        barcode: entry.code || null,
      })
    }
    let release = choice.release
    if (entry.code && !release.barcodes.includes(entry.code)) {
      try {
        release = await attachBarcode(release.id, entry.code)
      } catch (e) {
        // Added anyway; the entry tells why the code isn't remembered.
        entry.error = t('add.search.barcodeFailed', { message: message(e) })
      }
    }
    return release
  }

  /** Into the library (or onto Upcoming, if not out yet) with the round's details. */
  async function add(entry: ScanEntry, choice: Choice, platformId?: string): Promise<boolean> {
    entry.state = 'saving'
    entry.error = ''
    try {
      const release = await resolve(entry, choice, platformId)
      entry.release = release
      if (destinationFor(release) === 'track') {
        const libraryId = toValue(options.libraryId)
        entry.tracking = await tracker.mutateAsync({
          release_id: release.id,
          status: 'watching',
          library_id: libraryId || null,
        })
        entry.state = 'tracked'
      } else {
        entry.item = await creator.mutateAsync(toItemIn(release.id, options.details.value))
        entry.state = 'added'
      }
    } catch (e) {
      // Back to the choice, with the reason, so it can be fixed or picked again.
      if (!choicesOf(entry).length) entry.picked = choice
      entry.state = 'review'
      entry.error = message(e)
      activeId.value = entry.id
      return false
    }
    // No message: the queue shows it (✓), undo is one tap on the entry.
    if (activeId.value === entry.id && !entry.error) activeId.value = null
    return true
  }

  /** Added through the full form instead. */
  function settle(entry: ScanEntry, result: { item?: Item; tracking?: Tracking }) {
    entry.item = result.item ?? null
    entry.tracking = result.tracking ?? null
    entry.release = result.item?.release ?? result.tracking?.release ?? entry.release
    entry.state = result.item ? 'added' : 'tracked'
    if (activeId.value === entry.id) activeId.value = null
  }

  async function undo(entry: ScanEntry) {
    try {
      if (entry.item) await remover.mutateAsync(entry.item.id)
      if (entry.tracking) await untracker.mutateAsync(entry.tracking.id)
    } catch (e) {
      entry.error = message(e)
      activeId.value = entry.id
      return
    }
    discard(entry)
  }

  /** Another copy of the same game. */
  async function again(entry: ScanEntry) {
    if (!entry.release) return
    const copy = create(entry.code, 'saving')
    copy.lookup = entry.lookup
    if (activeId.value === entry.id) activeId.value = null
    await add(copy, { kind: 'release', release: entry.release })
  }

  function discard(entry: ScanEntry) {
    entries.value = entries.value.filter((e) => e.id !== entry.id)
    if (activeId.value === entry.id) activeId.value = null
  }

  /** A game picked in the search for this entry (or for a new one without a code). */
  function pick(entry: ScanEntry | null, choice: Choice): ScanEntry {
    const target = entry ?? create('', 'review')
    target.picked = choice
    target.state = 'review'
    target.error = ''
    activeId.value = target.id
    return target
  }

  function open(entry: ScanEntry) {
    activeId.value = entry.id
  }

  function close() {
    activeId.value = null
  }

  return {
    entries,
    active,
    done,
    scan,
    retry: look,
    add,
    resolve,
    settle,
    undo,
    again,
    discard,
    pick,
    open,
    close,
    destinationFor,
  }
}
