import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import ResizeHandle from '@/components/app/ResizeHandle.vue'
import { useUiStore } from '@/stores/ui'
import { renderComponent, settle } from '@/test/utils'

describe('resize handle', () => {
  async function mountHandle(edge: 'left' | 'right') {
    const width = ref(300)
    const dragging: boolean[] = []
    const Host = defineComponent({
      setup: () => () =>
        h('div', { style: 'position: relative' }, [
          h(ResizeHandle, {
            modelValue: width.value,
            'onUpdate:modelValue': (v: number) => (width.value = v),
            onDragging: (v: boolean) => dragging.push(v),
            edge,
            min: 200,
            max: 500,
            defaultWidth: 256,
            label: 'Width',
          }),
        ]),
    })
    const { wrapper } = await renderComponent(Host)
    return { width, dragging, handle: wrapper.find('[data-testid="resize-handle"]') }
  }

  it('drags, clamps and resets', async () => {
    const { width, dragging, handle } = await mountHandle('right')
    handle.element.dispatchEvent(
      new MouseEvent('pointerdown', { button: 0, clientX: 100, bubbles: true }),
    )
    await settle()
    expect(document.body.style.cursor).toBe('col-resize')
    window.dispatchEvent(new MouseEvent('pointermove', { clientX: 150 }))
    expect(width.value).toBe(350)
    window.dispatchEvent(new MouseEvent('pointermove', { clientX: 900 }))
    expect(width.value).toBe(500)
    window.dispatchEvent(new MouseEvent('pointerup'))
    expect(dragging).toEqual([true, false])
    expect(document.body.style.cursor).toBe('')
    handle.element.dispatchEvent(
      new MouseEvent('pointerdown', { button: 2, clientX: 100, bubbles: true }),
    )
    await settle()
    expect(dragging).toHaveLength(2)
    await handle.trigger('dblclick')
    await settle()
    expect(width.value).toBe(256)
  })

  it('grows towards the left for right-hand panels and works with the keyboard', async () => {
    const { width, handle } = await mountHandle('left')
    handle.element.dispatchEvent(
      new MouseEvent('pointerdown', { button: 0, clientX: 500, bubbles: true }),
    )
    await settle()
    window.dispatchEvent(new MouseEvent('pointermove', { clientX: 450 }))
    expect(width.value).toBe(350)
    window.dispatchEvent(new MouseEvent('pointerup'))
    await settle()
    await handle.trigger('keydown', { key: 'ArrowLeft' })
    expect(width.value).toBe(366)
    await handle.trigger('keydown', { key: 'ArrowRight', shiftKey: true })
    expect(width.value).toBe(302)
    await handle.trigger('keydown', { key: 'Home' })
    expect(width.value).toBe(200)
    await handle.trigger('keydown', { key: 'End' })
    expect(width.value).toBe(500)
    await handle.trigger('keydown', { key: 'a' })
    expect(width.value).toBe(500)
  })
})

describe('layout preferences', () => {
  it('remembers widths, detail column and cover size', async () => {
    setActivePinia(createPinia())
    const ui = useUiStore()
    ui.sidebarWidth = 320
    ui.detailPane = true
    ui.detailWidth = 600
    ui.gridSize = 'l'
    await nextTick()
    setActivePinia(createPinia())
    const again = useUiStore()
    expect([again.sidebarWidth, again.detailPane, again.detailWidth, again.gridSize]).toEqual([
      320,
      true,
      600,
      'l',
    ])
    localStorage.setItem('shelvd.grid-size', '"xl"')
    localStorage.setItem('shelvd.sidebar-width', 'not json')
    setActivePinia(createPinia())
    expect(useUiStore().gridSize).toBe('m')
    expect(useUiStore().sidebarWidth).toBe(256)
  })
})
