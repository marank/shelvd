import { DOMWrapper } from '@vue/test-utils'
import type { Library, Loan, Location, Member, Person } from '@/api/types'

export const LIB = '11111111-1111-1111-1111-111111111111'

export function library(
  role: 'owner' | 'editor' | 'viewer',
  extra: Partial<Library> = {},
): Library {
  return {
    id: LIB,
    name: 'Games',
    description: 'All my games',
    owner: role === 'owner' ? 'alice' : 'bob',
    role,
    item_count: 3,
    public_token: null,
    viewer_loans: 'status',
    created_at: '2026-01-01T00:00:00Z',
    ...extra,
  }
}

export function loan(extra: Partial<Loan> = {}): Loan {
  return {
    id: 'loan-1',
    item_id: 'item-1',
    item_title: 'Mario Kart 8',
    platform: 'Switch',
    cover_url: null,
    cover_aspect: null,
    borrower: { id: 'p1', name: 'Carol' },
    lent_on: '2026-10-01',
    due_on: '2026-10-15',
    returned_on: null,
    notes: '',
    overdue: false,
    ...extra,
  }
}

export function location(extra: Partial<Location> & { id: string; name: string }): Location {
  return { parent_id: null, kind: 'other', notes: '', path: extra.name, item_count: 0, ...extra }
}

export function person(extra: Partial<Person> & { id: string; name: string }): Person {
  return { email: '', notes: '', open_loans: 0, ...extra }
}

export function member(extra: Partial<Member> & { id: string; username: string }): Member {
  return { role: 'viewer', ...extra }
}

/** Query the whole document (dialogs are teleported to body). */
export function $(selector: string): DOMWrapper<HTMLElement> {
  const el = document.body.querySelector<HTMLElement>(selector)
  if (!el) throw new Error(`Not found: ${selector}`)
  return new DOMWrapper(el)
}

export function $$(selector: string): DOMWrapper<HTMLElement>[] {
  return [...document.body.querySelectorAll<HTMLElement>(selector)].map((el) => new DOMWrapper(el))
}

export function exists(selector: string): boolean {
  return !!document.body.querySelector(selector)
}
