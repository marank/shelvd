/**
 * Every value of a generated enum, in the order given. Written as the keys of a record, so the
 * type check fails when the backend adds a value that is missing here (or drops one still listed).
 * Pass the enum type explicitly: allValues<Schemas['LocationKind']>({ room: true, … }).
 * (`Schemas` from `@/api/types` = the generated `components['schemas']`.)
 */
export const allValues = <T extends string>(values: Record<T, true>): T[] =>
  Object.keys(values) as T[]
