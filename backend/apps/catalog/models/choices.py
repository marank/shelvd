from django.db import models


class MediaType(models.TextChoices):
    """Kind of medium: games, figures (amiibo …); video is reserved for DVD/Blu-ray."""

    GAME = "game"
    VIDEO = "video"
    TOY = "toy"  # figures like amiibo


class Region(models.TextChoices):
    """Release region as printed on the box. PAL covers Europe/Australia in general."""

    PAL = "pal"
    DE = "de"
    UK = "uk"
    FR = "fr"
    NA = "na"
    JP = "jp"
    ASIA = "asia"
    KR = "kr"
    WORLD = "world"
    OTHER = "other"


class DatePrecision(models.TextChoices):
    """How exact a release date is: "28.04.2017", "March 2026", "Q3 2026", "TBA" …

    The release stores the first day of the period; the end and the sort date follow
    from it (models/dates.py).
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    HALF = "half"
    YEAR = "year"
    WINDOW = "window"  # explicit start and end
    TBA = "tba"


class ImageTone(models.TextChoices):
    """How a picture with a transparent background reads (core.services.images.image_tone):
    a one-colour logo or one in colour that would vanish on a dark or a light background."""

    BLACK = "black"
    DARK = "dark"
    WHITE = "white"
    LIGHT = "light"


class PlatformIcon(models.TextChoices):
    """Neutral symbols for platform badges (the frontend maps them to icons); no logos."""

    CONSOLE = "console"
    CONTROLLER = "controller"
    JOYSTICK = "joystick"
    HANDHELD = "handheld"
    TABLET = "tablet"
    PHONE = "phone"
    PC = "pc"
    LAPTOP = "laptop"
    TV = "tv"
    DISC = "disc"
    CARTRIDGE = "cartridge"
    VR = "vr"
    FIGURE = "figure"
    FILM = "film"
