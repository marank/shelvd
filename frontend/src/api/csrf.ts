export function getCsrfToken(): string | undefined {
  return document.cookie
    .split('; ')
    .find((c) => c.startsWith('csrftoken='))
    ?.split('=')[1]
}

export async function ensureCsrf(): Promise<void> {
  if (!getCsrfToken()) await fetch('/api/auth/csrf', { credentials: 'same-origin' })
}
