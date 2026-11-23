/** How a picture with a transparent background reads – measured once on the server when it's
 * stored (`image_tone`, `photo_tone`): `black` / `white` (a one-colour logo, lost on a dark /
 * light background – shown inverted there), `dark` / `light` (a picture in colour that's
 * mostly dark / light – it gets a rim there), or `''` (it stands out anyway, or brings its
 * own background). */
export type ImageTone = 'black' | 'dark' | 'white' | 'light' | ''

/** Static class names for the box around the picture (Tailwind only sees whole ones): an
 * inverted logo, or a hairline outline (twice, so small logos hold it) plus a soft glow drawn
 * along the picture's shape. */
export const RIMS: Record<ImageTone, string> = {
  // Inverted with the hue turned back, so a few coloured details keep their colour.
  black: 'dark:[&_img]:[filter:invert(1)_hue-rotate(180deg)]',
  white: '[&_img]:[filter:invert(1)_hue-rotate(180deg)] dark:[&_img]:[filter:none]',
  dark: 'dark:[&_img]:[filter:drop-shadow(0_0_1px_rgb(255_255_255/0.85))_drop-shadow(0_0_1px_rgb(255_255_255/0.5))_drop-shadow(0_0_8px_rgb(255_255_255/0.28))]',
  light:
    '[&_img]:[filter:drop-shadow(0_0_1px_rgb(0_0_0/0.7))_drop-shadow(0_0_1px_rgb(0_0_0/0.4))_drop-shadow(0_0_8px_rgb(0_0_0/0.2))] dark:[&_img]:[filter:none]',
  '': '',
}

/** A photo is never inverted (a black console would turn white): it gets the rim. */
const PHOTO: Partial<Record<ImageTone, ImageTone>> = { black: 'dark', white: 'light' }

/** What keeps a picture of that tone visible without setting it apart from its neighbours. */
export function rimFor(tone: string | null | undefined, photo = false): string {
  const known = (tone && tone in RIMS ? tone : '') as ImageTone
  return RIMS[photo ? (PHOTO[known] ?? known) : known]
}
