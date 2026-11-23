from io import BytesIO
from typing import cast

from PIL import Image, ImageDraw

from apps.core.services.images import clear_background


def picture(background: tuple[int, int, int], fmt: str = "JPEG") -> bytes:
    image = Image.new("RGB", (40, 30), background)
    ImageDraw.Draw(image).rectangle((10, 8, 30, 22), fill=(200, 0, 0))
    out = BytesIO()
    image.save(out, fmt)
    return out.getvalue()


def test_a_white_background_becomes_transparent() -> None:
    cleared = clear_background(picture((255, 255, 255)))
    with Image.open(BytesIO(cleared)) as image:
        assert image.format == "PNG"
        rgba = image.convert("RGBA")
        assert cast(tuple[int, ...], rgba.getpixel((0, 0)))[3] == 0  # corner: gone
        assert cast(tuple[int, ...], rgba.getpixel((20, 15)))[3] == 255  # the logo stays


def test_other_pictures_stay_as_they_are() -> None:
    coloured = picture((0, 80, 160))
    assert clear_background(coloured) is coloured
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="white"/></svg>'
    assert clear_background(svg) is svg
    assert clear_background(b"no picture") == b"no picture"


def logo(
    colour: tuple[int, int, int, int], fill: tuple[int, int, int, int] = (0, 0, 0, 0)
) -> bytes:
    image = Image.new("RGBA", (40, 30), fill)
    ImageDraw.Draw(image).rectangle((10, 8, 30, 22), fill=colour)
    out = BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def svg(body: str, size: str = 'viewBox="0 0 100 40"') -> bytes:
    return f'<svg xmlns="http://www.w3.org/2000/svg" {size}>{body}</svg>'.encode()


def box(x: int, w: int, fill: str = "", extra: str = "") -> str:
    """A 100 × 40 picture's shape: x … x + w wide, 10 … 30 high."""
    colour = f' fill="{fill}"' if fill else ""
    return f'<rect x="{x}" y="10" width="{w}" height="20"{colour}{extra}/>'


def test_how_a_picture_reads() -> None:
    from apps.core.services.images import image_tone

    assert image_tone(logo((10, 10, 10, 255))) == "black"
    assert image_tone(logo((120, 10, 10, 255))) == "dark"
    assert image_tone(logo((250, 250, 250, 255))) == "white"
    assert image_tone(logo((255, 230, 180, 255))) == "light"
    assert image_tone(logo((10, 10, 10, 255), fill=(255, 255, 255, 255))) == ""  # own background
    assert image_tone(logo((0, 0, 0, 0))) == ""  # nothing drawn
    # SVGs are drawn first (resvg): what counts is what you see, by its area.
    assert image_tone(svg(box(10, 80))) == "black"  # unfilled shapes are black
    assert image_tone(svg(box(10, 80, "#9f9f9f") + box(30, 60, "#373536"))) == "black"
    assert image_tone(svg(box(10, 80, "#1060e0") + box(20, 60, "#111"))) == "dark"
    assert image_tone(svg(box(10, 80, "#fff"))) == "white"
    # Dark lettering with a few bright dots: outlined, so the dots keep their colour.
    dots = box(10, 80, "#121212") + '<circle cx="50" cy="20" r="5" fill="#def51f"/>'
    assert image_tone(svg(dots)) == "dark"
    # Colours from a <style> block and from the group they're in.
    styled = '<style>.a{fill:#ffe0a0}</style><g class="a">' + box(10, 80) + "</g>"
    assert image_tone(svg(styled)) == "light"
    # A blue word with black small print under it: the print would vanish, outlined.
    blizzard = box(10, 80, "#3c9be6") + '<rect x="20" y="31" width="60" height="3"/>'
    assert image_tone(svg(blizzard)) == "dark"
    assert image_tone(svg(box(10, 80, "#3c9be6"))) == ""  # the blue word alone stands out
    # Light letters with a dark rim: its own contrast, left as it is.
    assert image_tone(svg(box(10, 80, "#3D3938") + box(14, 72, "#D0C5C0"))) == ""
    # A size in mm resvg can't use: drawn by its viewBox.
    assert (
        image_tone(svg(box(10, 80), 'width="100mm%" height="4x" viewBox="0 0 100 40"')) == "black"
    )
    assert image_tone(svg("<g/>")) == ""  # nothing drawn
    assert image_tone(svg(box(0, 100) + '<rect width="100" height="40" fill="#123"/>')) == ""
    assert image_tone(b"<svg") == ""
    assert image_tone(b"no picture") == ""


def test_thin_lines_count() -> None:
    from apps.core.services.images import image_tone

    # A one-pixel black line on a large transparent picture: faint once scaled down.
    image = Image.new("RGBA", (1400, 660), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((100, 300, 1300, 302), fill=(0, 0, 0, 255))
    out = BytesIO()
    image.save(out, "PNG")
    assert image_tone(out.getvalue()) == "black"


def test_a_black_background_only_for_logos() -> None:
    on_black = picture((0, 0, 0), "PNG")
    assert clear_background(on_black) is on_black  # a photo keeps it
    with Image.open(BytesIO(clear_background(on_black, dark=True))) as image:
        rgba = image.convert("RGBA")
        assert cast(tuple[int, ...], rgba.getpixel((0, 0)))[3] == 0
        assert cast(tuple[int, ...], rgba.getpixel((20, 15)))[3] == 255


def test_a_picture_of_nothing_but_background_stays() -> None:
    blank = picture((255, 255, 255), "PNG")
    image = Image.new("RGB", (4, 4), (0, 0, 0))
    out = BytesIO()
    image.save(out, "PNG")
    assert clear_background(out.getvalue(), dark=True) == out.getvalue()
    assert clear_background(blank) != blank  # a logo on white still loses its background


def test_an_svg_loses_its_backdrop() -> None:
    def logo(backdrop: str, inside: str = "") -> bytes:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">'
            f'{inside}{backdrop}<path fill="#FFE81F" d="M10 10h80v30z"/></svg>'
        ).encode()

    black = logo('<rect x="-1" y="-1" width="102" height="52"/>')
    assert b"<rect" not in clear_background(black, dark=True)
    assert clear_background(black) is black  # black only for logos
    white = logo('<rect width="100" height="50" fill="white"></rect>')
    assert b"<rect" not in clear_background(white)
    # Not a backdrop: in colour, too small, styled, or inside a clip path.
    for kept in (
        logo('<rect width="100" height="50" fill="#006eb9"/>'),
        logo('<rect width="40" height="50"/>'),
        logo('<rect class="st0" width="100" height="50"/>'),
        logo("", '<clipPath><rect width="100" height="50"/></clipPath>'),
    ):
        assert clear_background(kept, dark=True) is kept
    assert clear_background(b"<svg", dark=True) == b"<svg"
