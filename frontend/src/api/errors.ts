export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface Result<T> {
  data?: T
  error?: unknown
  response: Response
}

function detailOf(error: unknown): string | undefined {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = error.detail
    if (typeof detail === 'string') return detail
    // Validation errors (422): [{msg, loc}, …]
    if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join(', ')
  }
  return undefined
}

/** Await an openapi-fetch call and return its data, or throw an ApiError with the
 * backend's message. */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await call
  if (!response.ok) {
    throw new ApiError(response.status, detailOf(error) ?? response.statusText)
  }
  return data as T
}
