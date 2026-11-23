export { cn } from 'cn'

/** The first value that is a non-empty string, for text where "" means "not set" too. */
export function firstText(...values: Array<string | null | undefined>): string | undefined {
  return values.find((v): v is string => v !== undefined && v !== null && v !== '')
}
