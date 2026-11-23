# Backlog

Ideas and follow-ups that are decided in principle but not built yet. Newest first within a section.

## Catalog

### Compilations: "contains" parts of a game
One cartridge, several games – e.g. *Monument: The Trilogy* holds three games, and Nintendo reports
each with its own title id.

- A game gets **parts** (e.g. a `WorkPart` model: work, title, position, external ids such as the
  HowLongToBeat id). Parts are **not** works: they never show up in libraries, the explorer or search.
- HowLongToBeat (and other facts) per part; the compilation's page shows each part and the sum.
- Add-ons that match external titles to games (play time) may want to point at a part.
- Touches catalog models/API, the game page and edit page, `providers/services/facts.py`,
  merging works (`catalog/services/merge.py`) and the IGDB import (IGDB knows bundles).

## Build

- Bundle budget is slightly over (initial ≈ 201/200 kB, total ≈ 402/400 kB): trim or raise
  `sizeBudget` in `frontend/package.json` deliberately.
