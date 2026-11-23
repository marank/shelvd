import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import type { Release } from '@/api/types'
import { formatReleaseDate, isOut, periodEnd, relativeHint } from '@/lib/releaseDate'
import DatePrecisionInput from '@/components/app/DatePrecisionInput.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import { renderComponent, settle } from '@/test/utils'

const d = (
  release_precision: Release['release_precision'],
  release_date: string | null,
  release_date_end: string | null = null,
) => ({
  release_precision,
  release_date,
  release_date_end,
})
const now = new Date(2026, 10, 1) // 1 Nov 2026

describe('release dates', () => {
  it('formats every precision', () => {
    expect(formatReleaseDate(d('day', '2017-04-28'), 'de')).toBe('28.04.2017')
    expect(formatReleaseDate(d('week', '2026-03-16'), 'de')).toBe('KW 12 2026')
    expect(formatReleaseDate(d('week', '2026-03-16'), 'en')).toBe('Week 12 2026')
    expect(formatReleaseDate(d('month', '2026-03-01'), 'de')).toBe('März 2026')
    expect(formatReleaseDate(d('quarter', '2026-07-01'), 'en')).toBe('Q3 2026')
    expect(formatReleaseDate(d('half', '2026-07-01'), 'en')).toBe('H2 2026')
    expect(formatReleaseDate(d('half', '2026-01-01'), 'en')).toBe('H1 2026')
    expect(formatReleaseDate(d('year', '2027-01-01'), 'en')).toBe('2027')
    expect(formatReleaseDate(d('window', '2026-05-05', '2026-06-01'), 'de')).toBe(
      '05.05.–01.06.2026',
    )
    expect(formatReleaseDate(d('window', '2026-05-05'), 'de')).toBe('05.05.–05.05.2026')
    expect(formatReleaseDate(d('tba', null), 'de', 'TBA')).toBe('TBA')
    expect(formatReleaseDate(d('day', null), 'de')).toBe('')
  })

  it('computes period ends and whether a release is out', () => {
    expect(periodEnd(d('quarter', '2026-10-01'))).toEqual(new Date(2026, 11, 31))
    expect(periodEnd(d('month', '2026-02-01'))).toEqual(new Date(2026, 1, 28))
    expect(periodEnd(d('week', '2026-03-16'))).toEqual(new Date(2026, 2, 22))
    expect(periodEnd(d('half', '2026-01-01'))).toEqual(new Date(2026, 5, 30))
    expect(periodEnd(d('year', '2026-01-01'))).toEqual(new Date(2026, 11, 31))
    expect(periodEnd(d('window', '2026-01-01', '2026-02-01'))).toEqual(new Date(2026, 1, 1))
    expect(periodEnd(d('tba', null))).toBeNull()
    expect(isOut(d('day', '2026-10-01'), now)).toBe(true)
    expect(isOut(d('quarter', '2026-10-01'), now)).toBe(false)
    expect(isOut(d('tba', null), now)).toBe(false)
  })

  it('gives relative hints for future dates', () => {
    expect(relativeHint(d('day', '2026-11-01'), 'en', now)).toBe('today')
    expect(relativeHint(d('day', '2026-11-02'), 'en', now)).toBe('tomorrow')
    expect(relativeHint(d('day', '2026-11-05'), 'en', now)).toBe('in 4 days')
    expect(relativeHint(d('day', '2026-11-22'), 'en', now)).toBe('in 3 weeks')
    expect(relativeHint(d('day', '2027-02-10'), 'en', now)).toBe('in 3 months')
    expect(relativeHint(d('quarter', '2026-10-01'), 'en', now)).toBe('next month')
    expect(relativeHint(d('year', '2028-01-01'), 'en', now)).toBe('in 2 years')
    expect(relativeHint(d('day', '2020-01-01'), 'en', now)).toBe('')
    expect(relativeHint(d('tba', null), 'en', now)).toBe('')
  })

  it('renders a date with hint', async () => {
    const { wrapper } = await renderComponent(ReleaseDate, {
      props: { release: d('tba', null), hint: true },
    })
    expect(wrapper.text()).toBe('TBA')
  })

  it('edits a date with precision', async () => {
    const model = ref(d('day', '2026-08-15'))
    const Host = defineComponent({
      setup: () => () =>
        h(DatePrecisionInput, {
          modelValue: model.value,
          'onUpdate:modelValue': (v: typeof model.value) => (model.value = v),
        }),
    })
    const { wrapper } = await renderComponent(Host)
    const value = new Proxy({} as typeof model.value, {
      get: (_, key) => model.value[key as keyof typeof model.value],
    })
    const click = async (id: string) => {
      await wrapper.find(`[data-testid="${id}"]`).trigger('click')
      await settle()
    }
    const change = async (id: string, v: string) => {
      const select = wrapper.find(`[data-testid="${id}"]`)
      ;(select.element as HTMLSelectElement).value = v
      await select.trigger('change')
      await settle()
    }
    await click('precision-quarter')
    expect(value.release_precision).toBe('quarter')
    await change('date-quarter', '3')
    expect(value.release_date).toBe('2026-10-01')
    await change('date-year', '2027')
    expect(value.release_date).toBe('2027-10-01')
    await click('precision-month')
    await change('date-month', '2')
    expect(value.release_date).toBe('2027-02-01')
    await click('precision-half')
    await change('date-half', '7')
    expect(value.release_date).toBe('2027-07-01')
    await click('precision-window')
    await wrapper.find('[data-testid="date-end"]').setValue('2027-08-01')
    await settle()
    expect(value.release_date_end).toBe('2027-08-01')
    await wrapper.find('[data-testid="date-start"]').setValue('')
    await settle()
    expect(value.release_date).toBeNull()
    await click('precision-tba')
    expect(model.value).toEqual(d('tba', null))
    await click('precision-year')
    expect(value.release_precision).toBe('year')
    expect(value.release_date).toMatch(/^\d{4}-01-01$/)
  })
})
