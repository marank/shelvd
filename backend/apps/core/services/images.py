"""Validated image uploads (covers, platform icons) into file fields."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any, cast

import resvg_py
from defusedxml import DefusedXmlException
from defusedxml import ElementTree as DefusedET
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.utils.translation import gettext as _
from ninja.errors import HttpError
from PIL import Image, ImageDraw, UnidentifiedImageError


def replace_file(field: FieldFile, name: str, content: bytes) -> None:
    """Put `content` into the field, removing its old file (no orphans). Doesn't save the
    model; image fields fill their width/height fields – save those too."""
    if field:
        field.delete(save=False)
    field.save(name, ContentFile(content), save=False)


def store_image(field: ImageFieldFile, upload: UploadedFile[bytes], max_mb: int) -> None:
    """Check size and type (JPEG/PNG/WebP), replace the field's file. Doesn't save the model."""
    if upload.size is None or upload.size > max_mb * 1024 * 1024:
        raise HttpError(400, _("The image is too large."))
    try:
        with Image.open(upload) as image:
            image.verify()
            image_format = (image.format or "").lower()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise HttpError(400, _("This file is not an image.")) from exc
    if image_format not in {"jpeg", "png", "webp"}:
        raise HttpError(400, _("Only JPEG, PNG and WebP images are supported."))
    upload.seek(0)
    if field:
        field.delete(save=False)
    extension = "jpg" if image_format == "jpeg" else image_format
    field.save(f"cover.{extension}", upload, save=False)


SVG_FORBIDDEN = {"script", "foreignobject", "iframe", "embed", "object", "audio", "video"}


def _check_svg(data: bytes) -> None:
    """Reject SVGs that could run code or load anything: no scripts, no event handlers,
    no links except to their own elements (#id)."""
    try:
        root = DefusedET.fromstring(data)
    except (DefusedET.ParseError, DefusedXmlException) as exc:
        raise HttpError(400, _("This file is not an image.")) from exc
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise HttpError(400, _("This file is not an image."))
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() in SVG_FORBIDDEN:
            raise HttpError(400, _("This SVG contains scripts or links and can't be used."))
        for name, value in element.attrib.items():
            local = name.rsplit("}", 1)[-1].lower()
            text = value.strip().lower()
            if (
                local.startswith("on")
                or (local == "href" and not text.startswith("#"))
                or "javascript:" in text
                or ("url(" in text and "url(#" not in text)
            ):
                raise HttpError(400, _("This SVG contains scripts or links and can't be used."))


ICON_TYPES = {"svg": "image/svg+xml", "jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def icon_extension(data: bytes) -> str:
    """What an icon is ("svg", "jpg", "png", "webp"); raises 400 for anything else and
    for SVGs with scripts or links."""
    if data.lstrip()[:1] == b"<":
        _check_svg(data)
        return "svg"
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
            image_format = (image.format or "").lower()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise HttpError(400, _("This file is not an image.")) from exc
    if image_format not in {"jpeg", "png", "webp"}:
        raise HttpError(400, _("Only SVG, JPEG, PNG and WebP images are supported."))
    return "jpg" if image_format == "jpeg" else image_format


def store_icon(
    field: FieldFile, upload: UploadedFile[bytes], max_kb: int = 256, logo: bool = False
) -> None:
    """A small icon: SVG (checked for scripts and links) or JPEG/PNG/WebP – a plain white
    background made transparent (`clear_background`), for a `logo` a plain black one too.
    Replaces the field's file; doesn't save the model."""
    if upload.size is None or upload.size > max_kb * 1024:
        raise HttpError(400, _("The image is too large."))
    data = clear_background(upload.read(), dark=logo)
    extension = icon_extension(data)
    if field:
        field.delete(save=False)
    field.save(f"icon.{extension}", ContentFile(data), save=False)


def fit_picture(data: bytes, max_bytes: int = 2 * 1024 * 1024, max_side: int = 1600) -> bytes:
    """A raster picture made small enough to keep (photos from Commons are often many
    megabytes): scaled to `max_side` and saved as PNG (with transparency) or JPEG. SVGs and
    pictures that fit already stay as they are; anything that isn't a picture too."""
    if data.lstrip()[:1] == b"<" or len(data) <= max_bytes:
        return data
    try:
        with Image.open(BytesIO(data)) as image:
            image.thumbnail((max_side, max_side))
            out = BytesIO()
            if image.mode in ("RGBA", "LA", "P"):
                image.save(out, "PNG", optimize=True)
            else:
                image.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
    except UnidentifiedImageError, OSError, Image.DecompressionBombError:
        return data
    return out.getvalue()


# Shapes an SVG fills black unless told otherwise.
SVG_SHAPES = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "text"}
SVG_COLOR = re.compile(r"#([0-9a-f]{6}|[0-9a-f]{3})\b|rgb\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)")
NAMED_COLORS = {"black": (0, 0, 0), "white": (255, 255, 255), "currentcolor": (0, 0, 0)}


def _shade(r: float, g: float, b: float) -> tuple[float, float]:
    """(lightness, saturation), both 0…1."""
    lightness = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return lightness, (max(r, g, b) - min(r, g, b)) / 255


def _svg_colors(data: bytes) -> list[tuple[int, int, int]]:
    root = DefusedET.fromstring(data)
    return [
        color
        for element in root.iter()
        for value in _paint_values(element)
        if (color := _svg_color(value)) is not None
    ]


def _paint_values(element: Any) -> list[str]:
    """An SVG element's fill, stroke and stop colours, from attributes and its style."""
    attrs = {k.rsplit("}", 1)[-1]: v for k, v in element.attrib.items()}
    style = dict(part.split(":", 1) for part in attrs.get("style", "").split(";") if ":" in part)
    values = [
        str(v).strip().lower()
        for key in ("fill", "stroke", "stop-color")
        for v in (attrs.get(key), style.get(key))
        if v
    ]
    if not values and element.tag.rsplit("}", 1)[-1] in SVG_SHAPES:
        return ["black"]  # unfilled shapes are black
    return values


def _svg_color(value: str) -> tuple[int, int, int] | None:
    """A colour name, #rgb, #rrggbb or rgb(…) value; None for anything else (url(…))."""
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    match = SVG_COLOR.search(value)
    if match is None:
        return None
    if match.group(1):
        return _hex(match.group(1))
    return int(match[2]), int(match[3]), int(match[4])


def is_dark_mark(data: bytes) -> bool:
    """Whether an icon is a dark mark in one colour (a black glyph) – unreadable on a dark
    background, fine inverted. Colourful illustrations and pictures without transparency
    are not."""
    if data.lstrip()[:1] == b"<":
        try:
            colors = _svg_colors(data)
        except DefusedET.ParseError, DefusedXmlException:
            return False
        shades = [_shade(*c) for c in colors]
        dark = [s for s in shades if s[0] < 0.3 and s[1] < 0.25]
        return bool(shades) and not any(s[1] > 0.25 for s in shades) and len(dark) * 2 > len(shades)
    try:
        with Image.open(BytesIO(data)) as image:
            small = image.convert("RGBA")
            small.thumbnail((64, 64))
    except UnidentifiedImageError, OSError:
        return False
    rgba = cast(tuple[tuple[int, int, int, int], ...], small.get_flattened_data())
    pixels = [p for p in rgba if p[3] >= 128]
    if not pixels or len(pixels) == small.width * small.height:
        return False  # nothing to see, or no transparency: inverting gives a block
    shades = [_shade(r, g, b) for r, g, b, _a in pixels]
    lightness = sum(s[0] for s in shades) / len(shades)
    saturation = sum(s[1] for s in shades) / len(shades)
    light_share = sum(1 for s in shades if s[0] > 0.6) / len(shades)
    return lightness < 0.3 and saturation < 0.2 and light_share < 0.1


def _clear(image: Image.Image, dark: bool = False) -> bool:
    """Makes a plain light background (all four corners near-white and alike) – with `dark`
    also a plain black one – transparent, filling from the corners; what's inside the
    picture stays. Whether it did."""
    width, height = image.size
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    colours = [cast(tuple[int, int, int, int], image.getpixel(c)) for c in corners]
    light = all(c[3] == 255 and _shade(*c[:3])[0] > 0.85 for c in colours)
    black = dark and all(c[3] == 255 and _shade(*c[:3])[0] < 0.12 for c in colours)
    plain = light or black
    if not plain or max(max(c[:3]) - min(c[:3]) for c in zip(*colours, strict=False)) >= 24:
        return False
    cleared = image.copy()
    for corner in corners:
        ImageDraw.floodfill(cleared, corner, (0, 0, 0, 0), thresh=40)
    if cleared.getchannel("A").getbbox() is None:
        return False  # nothing but background: keep the picture as it is
    image.paste(cleared)
    return True


# SVG elements whose content isn't drawn where it stands.
SVG_HIDDEN = {"defs", "clippath", "mask", "pattern", "symbol", "marker", "lineargradient"}
SVG_ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')


def _number(value: str | None) -> float | None:
    try:
        return float((value or "").removesuffix("px"))
    except ValueError:
        return None


def _svg_box(root: Any) -> list[float] | None:
    """left, top, width and height of the picture: its viewBox, else its size."""
    box = [_number(v) for v in root.attrib.get("viewBox", "").replace(",", " ").split()]
    if len(box) != 4 or None in box:
        box = [0.0, 0.0, _number(root.attrib.get("width")), _number(root.attrib.get("height"))]
    if None in box:
        return None
    return cast(list[float], box)


def _first_shape(element: Any) -> Any:
    """The first shape drawn, in document order, outside definitions."""
    for child in element:
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in SVG_HIDDEN:
            continue
        if tag in SVG_SHAPES:
            return child
        if (found := _first_shape(child)) is not None:
            return found
    return None


def _covers_box(attrs: dict[str, str], box: list[float]) -> bool:
    """Whether a rectangle with these attributes covers the whole box (2 % slack)."""
    left, top, width, height = box
    x, y = _number(attrs.get("x", "0")), _number(attrs.get("y", "0"))
    w, h = _number(attrs.get("width")), _number(attrs.get("height"))
    if x is None or y is None or w is None or h is None:
        return False
    slack = 0.02 * max(width, height)
    return (
        x <= left + slack
        and y <= top + slack
        and x + w >= left + width - slack
        and y + h >= top + height - slack
    )


def _svg_backdrop(root: Any) -> dict[str, str] | None:
    """The attributes of a plain rectangle drawn first over the whole picture, if any."""
    box = _svg_box(root)
    if box is None:
        return None
    rect = _first_shape(root)
    if rect is None or rect.tag.rsplit("}", 1)[-1].lower() != "rect":
        return None
    attrs = {k.rsplit("}", 1)[-1]: v for k, v in rect.attrib.items()}
    fill = attrs.get("fill", "black").strip().lower()
    if not _covers_box(attrs, box) or "class" in attrs or "style" in attrs or "url(" in fill:
        return None
    return attrs


def _clear_svg(data: bytes, dark: bool) -> bytes:
    """An SVG without the plain rectangle it draws first over the whole picture (white, with
    `dark` black too) – removed from the text as it stands, so nothing else changes."""
    try:
        attrs = _svg_backdrop(DefusedET.fromstring(data))
    except DefusedET.ParseError, DefusedXmlException:
        return data
    if attrs is None:
        return data
    fill = attrs.get("fill", "black").strip().lower()
    match = SVG_COLOR.search(fill)
    rgb = NAMED_COLORS.get(fill) or (_hex(match.group(1)) if match and match.group(1) else None)
    if rgb is None:
        return data
    lightness = _shade(*rgb)[0]
    if not (lightness > 0.9 or (dark and lightness < 0.1)):
        return data
    text = data.decode("utf-8", "ignore")
    for tag in re.finditer(r"<rect\b[^>]*?(/>|>\s*</rect>|>)", text):
        if dict(SVG_ATTR.findall(tag.group(0))) == attrs:
            return (text[: tag.start()] + text[tag.end() :]).encode()
    return data


def _hex(code: str) -> tuple[int, int, int]:
    code = "".join(c * 2 for c in code) if len(code) == 3 else code
    return int(code[:2], 16), int(code[2:4], 16), int(code[4:], 16)


def clear_background(data: bytes, dark: bool = False) -> bytes:
    """A raster logo or photo on plain white – a logo (`dark`) also on plain black – as a PNG
    with that background transparent, so it sits on any background. Not for photos on black:
    a dark device would lose its edges. An SVG loses a plain rectangle drawn first over the
    whole picture; pictures with another background and anything that isn't a picture stay
    as they are."""
    if data.lstrip()[:1] == b"<":
        return _clear_svg(data, dark)
    try:
        with Image.open(BytesIO(data)) as source:
            image = source.convert("RGBA")
    except UnidentifiedImageError, OSError, Image.DecompressionBombError:
        return data
    if not _clear(image, dark):
        return data
    out = BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()


def _tone(shades: list[tuple[float, ...]], exposed: tuple[float, float] = (0.0, 0.0)) -> str:
    """`black` / `dark` (lost on a dark background; one colour or in colour), `white` /
    `light` (lost on a light one) or "" from the (lightness, saturation[, weight]) of what's
    drawn: dark on average with hardly anything light (mid grey fades too), or the other way
    round – or mid-toned with dark (light) parts on the background: `exposed` is their share
    of what's drawn."""
    if not shades:
        return ""
    weights = [s[2] if len(s) > 2 else 1.0 for s in shades]
    total = sum(weights)
    average = sum(s[0] * w for s, w in zip(shades, weights, strict=True)) / total
    # One colour: greyish on average and hardly any clearly coloured part (a few green dots
    # would turn dark when inverted).
    coloured = sum(w for s, w in zip(shades, weights, strict=True) if s[1] > 0.3)
    plain = (
        sum(s[1] * w for s, w in zip(shades, weights, strict=True)) / total < 0.12
        and coloured < total * 0.03
    )
    lightish = sum(w for s, w in zip(shades, weights, strict=True) if s[0] > 0.6)
    darkish = sum(w for s, w in zip(shades, weights, strict=True) if s[0] < 0.4)
    if average < 0.5 and lightish < total * 0.25:
        return "black" if plain else "dark"
    if average > 0.75 and darkish < total * 0.25:
        return "white" if plain else "light"
    # Otherwise dark parts right on the background (black small print under a blue word, dark
    # lettering beside a bright symbol) would vanish: outlined, not inverted (the rest is in
    # colour). Dark parts inside a coloured shape don't count: they don't touch it.
    if exposed[0] >= 0.03:
        return "dark"
    if exposed[1] >= 0.03:
        return "light"
    return ""


def _render_svg(data: bytes, side: int = 128) -> Image.Image | None:
    """An SVG drawn as a picture `side` pixels wide (resvg: what a browser shows – sizes,
    classes, gradients, masks), or None if it can't be drawn. A size in mm or % that resvg
    can't use is dropped; the viewBox keeps the proportions."""
    text = data.decode("utf-8", "ignore")
    head, svg, rest = text.partition("<svg")
    tag, close, body = rest.partition(">")
    sizeless = head + svg + re.sub(r"\s(width|height)\s*=\s*\"[^\"]*\"", "", tag) + close + body
    for markup in (text, sizeless):
        try:
            png = resvg_py.svg_to_bytes(svg_string=markup, width=side)
            with Image.open(BytesIO(bytes(png))) as image:
                return image.convert("RGBA")
        except ValueError, OSError, UnidentifiedImageError:
            continue
    return None


def image_tone(data: bytes) -> str:
    """How a picture with a transparent background reads (see `_tone`), so pages can keep it
    visible: invert a one-colour logo, outline the rest – by its pixels, an SVG drawn first.
    A picture without transparency brings its own background ("")."""
    if data.lstrip()[:1] == b"<":
        small = _render_svg(data)
        if small is None:
            return ""
    else:
        try:
            with Image.open(BytesIO(data)) as image:
                small = image.convert("RGBA")
                small.thumbnail((128, 128))
        except UnidentifiedImageError, OSError, Image.DecompressionBombError:
            return ""
    rgba = cast(tuple[tuple[int, int, int, int], ...], small.get_flattened_data())
    if sum(1 for p in rgba if p[3] == 255) > len(rgba) * 0.95:
        return ""  # its own background
    # Thin lines turn half transparent when scaled down: they count by how opaque they are.
    shades: list[tuple[float, ...]] = [
        (*_shade(r, g, b), a / 255) for r, g, b, a in rgba if a >= 32
    ]
    return _tone(shades, _exposed(rgba, small.width)) if shades else ""


def _exposed(rgba: tuple[tuple[int, int, int, int], ...], width: int) -> tuple[float, float]:
    """The shares of drawn pixels that are dark / light and touch the transparent background
    (a neighbour left, right, above or below is see-through): what vanishes on a dark / light
    page."""
    drawn = dark = light = 0
    for i, (r, g, b, a) in enumerate(rgba):
        if a < 128:
            continue
        drawn += 1
        x = i % width
        neighbours = (
            [i - width, i + width] + ([i - 1] if x else []) + ([i + 1] if x < width - 1 else [])
        )
        if not any(0 <= n < len(rgba) and rgba[n][3] < 32 for n in neighbours):
            continue
        lightness = _shade(r, g, b)[0]
        dark += lightness < 0.3
        light += lightness > 0.85
    return (dark / drawn, light / drawn) if drawn else (0.0, 0.0)


def make_icon(data: bytes, size: int = 256) -> bytes:
    """A raster picture as an icon: a plain light background (a product photo on white) made
    transparent, cut to what's left and scaled to `size` – a photo of the device makes a
    badge icon. SVGs and anything that isn't a picture stay as they are."""
    if data.lstrip()[:1] == b"<":
        return data
    try:
        with Image.open(BytesIO(data)) as source:
            image = source.convert("RGBA")
    except UnidentifiedImageError, OSError, Image.DecompressionBombError:
        return data
    image.thumbnail((size * 4, size * 4))
    _clear(image)
    box = image.getchannel("A").getbbox()
    if box:
        image = image.crop(box)
    side = max(image.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    square.thumbnail((size, size))
    out = BytesIO()
    square.save(out, "PNG", optimize=True)
    return out.getvalue()
