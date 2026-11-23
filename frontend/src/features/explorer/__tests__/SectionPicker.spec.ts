import { describe, expect, it, vi } from 'vitest'
import { openMenu, renderComponent, settle } from '@/test/utils'
import SectionPicker from '../components/SectionPicker.vue'

describe('section picker', () => {
  it('picks a field', async () => {
    const update = vi.fn<(value: string) => void>()
    await renderComponent(SectionPicker, {
      props: { modelValue: '', 'onUpdate:modelValue': update },
    })
    expect(document.body.textContent).toContain('Sections')
    await openMenu('section-picker')
    ;(document.querySelector('[data-testid="section-platform.name"]') as HTMLElement).click()
    await settle()
    expect(update).toHaveBeenCalledWith('platform.name')
  })

  it('shows the field and clears it again', async () => {
    const update = vi.fn<(value: string) => void>()
    await renderComponent(SectionPicker, {
      props: { modelValue: 'platform.name', 'onUpdate:modelValue': update },
    })
    expect(document.querySelector('[data-testid="section-picker"]')?.textContent).toContain(
      'Platform',
    )
    await openMenu('section-picker')
    ;(document.querySelector('[data-testid="section-none"]') as HTMLElement).click()
    await settle()
    expect(update).toHaveBeenCalledWith('')
  })
})
