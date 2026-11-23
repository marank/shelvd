import { describe, expect, it } from 'vitest'
import { richText } from '@/lib/richText'

describe('richText', () => {
  it('keeps simple formatting and drops the newlines around blocks', () => {
    expect(
      richText('Intro.\n\n<ul><li><b>SWORDFIGHT:</b> \nParry</li>\n<li>Quick Draw</li></ul>\nEnd'),
    ).toBe('Intro.<ul><li><b>SWORDFIGHT:</b> \nParry</li><li>Quick Draw</li></ul>End')
  })

  it('strips attributes, unknown tags and anything executable', () => {
    expect(
      richText(
        '<b onclick="x()" class="y">bold</b><a href="javascript:x()">link</a>' +
          '<img src=x onerror=alert(1)><script>alert(1)</script><style>*{}</style>',
      ),
    ).toBe('<b>bold</b>link')
  })

  it('escapes text', () => {
    expect(richText('1 < 2 & "quotes"')).toBe('1 &lt; 2 &amp; "quotes"')
    expect(richText('')).toBe('')
  })
})
