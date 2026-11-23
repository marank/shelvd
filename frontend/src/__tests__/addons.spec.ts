import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { addons, collect, useAddonFigures, type Addon } from '@/addons'
import ImportCard from '@/features/manage/components/settings/ImportCard.vue'
import { makeLibrary } from '@/test/fixtures'
import { renderComponent } from '@/test/utils'

// The public repository ships without add-ons (src/addons/<name>/ is git-ignored); a
// checkout may have some installed, so they are set aside here.
describe('add-ons, none installed', () => {
  let installed: Addon[] = []
  beforeEach(() => {
    installed = addons.splice(0)
  })
  afterEach(() => {
    addons.push(...installed)
  })

  it('contribute nothing', () => {
    expect(collect('routes')).toEqual([])
    expect(collect('nav').flat()).toEqual([])
    expect(useAddonFigures(() => ({ workId: 'w', platformId: null })).value).toEqual([])
  })

  it("leave out a library's import card", async () => {
    await renderComponent(ImportCard, { props: { library: makeLibrary() } })
    expect(document.querySelector('[data-testid="settings-import"]')).toBeNull()
  })
})
