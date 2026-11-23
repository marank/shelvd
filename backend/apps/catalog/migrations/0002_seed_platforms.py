"""Initial platforms with their IGDB ids. More can be added in the admin at any time."""

from typing import Any

from django.db import migrations

# (name, short name, slug, manufacturer, year, IGDB platform id)
PLATFORMS = [
    ("Nintendo Entertainment System", "NES", "nes", "Nintendo", 1983, 18),
    ("Super Nintendo", "SNES", "snes", "Nintendo", 1990, 19),
    ("Nintendo 64", "N64", "n64", "Nintendo", 1996, 4),
    ("Nintendo GameCube", "GC", "gamecube", "Nintendo", 2001, 21),
    ("Nintendo Wii", "Wii", "wii", "Nintendo", 2006, 5),
    ("Nintendo Wii U", "Wii U", "wii-u", "Nintendo", 2012, 41),
    ("Nintendo Switch", "Switch", "switch", "Nintendo", 2017, 130),
    ("Nintendo Switch 2", "Switch 2", "switch-2", "Nintendo", 2025, 508),
    ("Game Boy", "GB", "game-boy", "Nintendo", 1989, 33),
    ("Game Boy Color", "GBC", "game-boy-color", "Nintendo", 1998, 22),
    ("Game Boy Advance", "GBA", "game-boy-advance", "Nintendo", 2001, 24),
    ("Nintendo DS", "DS", "nds", "Nintendo", 2004, 20),
    ("Nintendo 3DS", "3DS", "3ds", "Nintendo", 2011, 37),
    ("New Nintendo 3DS", "New 3DS", "new-3ds", "Nintendo", 2014, 137),
    ("PlayStation", "PS1", "ps1", "Sony", 1994, 7),
    ("PlayStation 2", "PS2", "ps2", "Sony", 2000, 8),
    ("PlayStation 3", "PS3", "ps3", "Sony", 2006, 9),
    ("PlayStation 4", "PS4", "ps4", "Sony", 2013, 48),
    ("PlayStation 5", "PS5", "ps5", "Sony", 2020, 167),
    ("PlayStation Portable", "PSP", "psp", "Sony", 2004, 38),
    ("PlayStation Vita", "Vita", "ps-vita", "Sony", 2011, 46),
    ("Xbox", "Xbox", "xbox", "Microsoft", 2001, 11),
    ("Xbox 360", "X360", "xbox-360", "Microsoft", 2005, 12),
    ("Xbox One", "XONE", "xbox-one", "Microsoft", 2013, 49),
    ("Xbox Series X|S", "XSX", "xbox-series", "Microsoft", 2020, 169),
    ("Sega Master System", "SMS", "master-system", "Sega", 1985, 64),
    ("Sega Mega Drive", "MD", "mega-drive", "Sega", 1988, 29),
    ("Sega Saturn", "Saturn", "saturn", "Sega", 1994, 32),
    ("Sega Dreamcast", "DC", "dreamcast", "Sega", 1998, 23),
    ("Sega Game Gear", "GG", "game-gear", "Sega", 1990, 35),
    ("PC (Windows)", "PC", "pc", "", 1985, 6),
]


def seed(apps: Any, schema_editor: Any) -> None:
    Platform = apps.get_model("catalog", "Platform")
    for name, short, slug, manufacturer, year, igdb in PLATFORMS:
        Platform.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "short_name": short,
                "manufacturer": manufacturer,
                "release_year": year,
                "external_ids": {"igdb": igdb},
            },
        )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
