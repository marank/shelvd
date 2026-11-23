/**
 * Justified rows for covers of different shapes: every cover in a row has the same
 * height, full rows fill the width exactly, and the last row takes the previous row's
 * height (so it isn't smaller or stretched). Returns the width of each card.
 */
export interface JustifyOptions {
  /** Available width in px. */
  width: number
  /** Desired cover height in px. */
  rowHeight: number
  /** Horizontal gap between cards. */
  gap: number
  /** Extra width per card besides the cover (padding). */
  padding: number
}

export function justify(aspects: number[], options: JustifyOptions): number[] {
  const { width, rowHeight, gap, padding } = options
  const widths: number[] = Array.from({ length: aspects.length }, () => 0)
  let row: number[] = []
  let sum = 0
  let lastHeight = rowHeight

  const place = (indices: number[], height: number) => {
    for (const i of indices) widths[i] = Math.floor(aspects[i]! * height + padding)
  }
  // Height at which the given cards exactly fill the width.
  const fillHeight = (count: number, aspectSum: number) =>
    (width - count * padding - (count - 1) * gap) / aspectSum

  aspects.forEach((aspect, index) => {
    const natural = (sum + aspect) * rowHeight + (row.length + 1) * padding + row.length * gap
    if (natural < width || !row.length) {
      row.push(index)
      sum += aspect
      return
    }
    // The row is full: close it with or without this cover, whichever height is
    // closer to the target (so rows neither shrink nor grow much).
    const without = fillHeight(row.length, sum)
    const withIt = fillHeight(row.length + 1, sum + aspect)
    if (Math.abs(withIt - rowHeight) < Math.abs(without - rowHeight)) {
      row.push(index)
      place(row, withIt)
      lastHeight = withIt
      row = []
      sum = 0
    } else {
      place(row, without)
      lastHeight = without
      row = [index]
      sum = aspect
    }
  })
  if (row.length) {
    // The last row: same height as the one before, but never wider than the space.
    place(row, Math.min(lastHeight, fillHeight(row.length, sum)))
  }
  return widths
}
