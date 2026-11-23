/** Query keys in one place, so mutations invalidate exactly what they change. */
export const keys = {
  libraries: ['libraries'] as const,
  library: (id: string) => ['libraries', id] as const,
  items: (libraryId: string) => ['items', libraryId] as const,
  tree: (libraryId: string) => ['tree', libraryId] as const,
  item: (libraryId: string, itemId: string) => ['items', libraryId, 'one', itemId] as const,
  overviews: (libraryId: string) => ['overviews', libraryId] as const,
  locations: (libraryId: string) => ['locations', libraryId] as const,
  people: (libraryId: string) => ['people', libraryId] as const,
  loans: (libraryId: string) => ['loans', libraryId] as const,
  members: (libraryId: string) => ['members', libraryId] as const,
  platforms: ['platforms'] as const,
  lists: ['lists'] as const,
  list: (id: string) => ['lists', id] as const,
  providers: ['providers'] as const,
  work: (id: string) => ['works', id] as const,
  trackings: ['trackings'] as const,
}
