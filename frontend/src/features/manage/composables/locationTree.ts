import { Armchair, DoorOpen, LibraryBig, MapPin, Package } from '@lucide/vue'
import type { Location, Schemas } from '@/api/types'
import { allValues } from '@/utils/enums'

export type LocationKind = Schemas['LocationKind']
export const LOCATION_KINDS = allValues<LocationKind>({
  room: true,
  furniture: true,
  shelf: true,
  box: true,
  other: true,
})

export const KIND_ICONS = {
  room: DoorOpen,
  furniture: Armchair,
  shelf: LibraryBig,
  box: Package,
  other: MapPin,
} as const

export interface LocationTreeNode {
  location: Location
  children: LocationTreeNode[]
}

/** Turn the flat list into a forest; places whose parent is missing become roots. */
export function buildTree(locations: Location[]): LocationTreeNode[] {
  const nodes = new Map<string, LocationTreeNode>()
  for (const location of locations) nodes.set(location.id, { location, children: [] })
  const roots: LocationTreeNode[] = []
  for (const node of nodes.values()) {
    const parent = node.location.parent_id ? nodes.get(node.location.parent_id) : undefined
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  const sort = (list: LocationTreeNode[]) => {
    list.sort((a, b) => a.location.name.localeCompare(b.location.name))
    list.forEach((n) => sort(n.children))
  }
  sort(roots)
  return roots
}

/** Ids of a place and everything below it (it can't be moved there). */
export function subtreeIds(locations: Location[], id: string): Set<string> {
  const result = new Set([id])
  let grew = true
  while (grew) {
    grew = false
    for (const l of locations) {
      if (l.parent_id && result.has(l.parent_id) && !result.has(l.id)) {
        result.add(l.id)
        grew = true
      }
    }
  }
  return result
}
