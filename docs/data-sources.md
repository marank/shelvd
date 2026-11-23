# Data sources for games (and later films)

Researched November 2026. Some terms pages refused automated access; entries marked (S) come from
secondary sources — check the provider's own terms before relying on them.

## Comparison

| Source | Cost / licence | Access | Regions & covers | Barcode | Handheld/retro | Status |
|---|---|---|---|---|---|---|
| **IGDB** (Twitch) | free for non-commercial use, attribution expected; commercial needs a partner agreement (S) | Twitch client credentials, ~4 req/s, no CORS (backend only) | release dates per region/platform, publishers/developers, genres, covers, localized titles | no | very good (NDS, 3DS, retro, Switch 2) | active |
| MobyGames | API no longer free since 2024 (S) | API key, low hourly limits | excellent per-country releases and regional cover scans | no | excellent | active, paid |
| TheGamesDB | free, key on request | monthly allowance per key | region field, front/back box art | no | good | active |
| ScreenScraper.fr | only for free software, otherwise permission needed (S) | user login (dev id optional), throttled | very good regional box art (2D/3D) | no (ROM hashes) | excellent (retro) | active, often overloaded |
| RAWG | free up to 100k MAU, backlink required (S) | key, 20k req/month | weak on regions | no | medium | active, little curation |
| Giant Bomb | non-commercial free | key, 200 req/resource/h | releases with region | no | good | uncertain in 2026 |
| GameTDB | licence unclear | XML dumps | IDs with region code, regional covers | not confirmed | Wii/GC/DS/3DS/Switch | active |
| LaunchBox DB | no official terms/API | daily XML dump | dates, images per region | no | very good | active |
| **PriceCharting** | paid subscription; data must be deleted when it ends | token | console name distinguishes PAL/JP | **yes (UPC lookup)** | very good | active |
| **UPCitemdb** | free 100 lookups/day; paid plans (S) | none (trial) / key | generic product title only | yes (generic) | random | removed: European game titles were unusable |
| EAN-Search, Go-UPC, barcodelookup | paid / trial | key | generic title only | yes (generic) | random | active |
| **Wikidata / Wikipedia** | CC0 (Wikidata), CC BY-SA (article texts) | API, no key, descriptive User-Agent | platforms, companies, genres; localized titles and descriptions; cross-IDs (IGDB P5794) | property P3962 exists, almost empty for games | good | active |
| TMDB (films) | non-commercial free, attribution required | key | release dates per country, posters | no | – | active |

## The hard part: barcode → game + platform + region

No free source maps game barcodes reliably. PriceCharting is the only specialised one (paid).
Generic product databases return shop titles. We tried UPCitemdb: of seven games scanned in Germany
only three led to a hit, the others came back as "Nintendo Wii U Game: Mario Kart 8 Wiiu Pal Version &
Original Package" or not at all, so shelvd doesn't use one. The GS1 prefix doesn't tell the region either: it says where the code was
registered, and Nintendo's European boxes carry US codes (0045496…).

**So the valuable asset is our own `catalog.Barcode` table**: every scan a user confirms is stored and
answers the next scan of that code without asking anyone.

## What shelvd does

- Scan flow (`apps/providers/services/lookup.py`): normalize the GTIN (UPC-A → GTIN-13, check digit) →
  local `Barcode` table → if unknown, title search (IGDB), no barcode source is asked →
  user picks candidate, platform and region → `services/importer.py` stores
  work, release, companies, genres and downloads the cover → barcode saved as confirmed.
- Manual entry always works, even without any source configured.
- Covers are stored locally under `DATA_DIR/media/covers` (provider image hosts are not for hotlinking);
  only search previews load from `images.igdb.com`.
- Every source is optional and set up by an admin in the app (**Integrations**): on/off, keys (stored
  encrypted with a key derived from `SECRET_KEY`), a "test connection" button, the last success and
  error. Everyone sees which are active and the attribution.
- **Matching a game** with a metadata source ("Match game data …" on the game page): one entry,
  the page switches between the switched-on sources (`MetadataSource.catalog` says whether a
  source can also add games; `fields` what it can fill in). Sources answer in the interface's
  language (`Accept-Language` → `get_language()`): IGDB gives its "German title" alternative
  name and German genre names (its fixed list, `GENRES_DE`) – its descriptions are English only.
  **Wikipedia** (via Wikidata, no key, CC BY-SA) adds titles, descriptions (the article's
  introduction, with a source line) and the first release date in German or English; it only
  completes games, it never adds any. A different title is always only offered, never preselected.
- **Matching the whole catalog** (`manage.py match_metadata [--apply] [--work <id>] [--fresh]`,
  `services/bulk_match.py`): a dry run by default, printing per game what it would take (`+`) and
  what it leaves (`·`). A game is matched only when the source has exactly one game of that title
  (German or its own, compared like names) on one of its release platforms, or it was linked
  before; anything else is reported as unsure. It takes empty fields, more precise dates (only
  within our period) and a first release later than the source's (or 1 June of the same year –
  year-only data); other differences and every picture stay as they are. IGDB's answers are kept
  under `DATA_DIR/answers/igdb` (`igdb.saved_answers`), so the real run doesn't ask again;
  `--fresh` does. 429s are retried with growing waits.
- **Descriptions of companies, series and platforms** (`DescriptionSource`: Wikipedia; IGDB for companies and platforms): on their page,
  "Description from Wikipedia …" lists entries for the name (companies and franchises/series
  first, games left out, each with Wikidata's short description); the picked one's introduction
  becomes the description (with the source line) and its id is kept in `external_ids`. Genres
  aren't described this way – they're too general for an article.
  "Choose picture …" lists every picture of the entries a term is linked to (all logos a Wikidata
  entry lists, older ones too, and IGDB's logo); they reach the browser only as encrypted tokens,
  previews go through the server and are checked like uploads.
- **Play times and scores** (HowLongToBeat, OpenCritic) are cached per game (`catalog.WorkFact`) and
  shared by everyone. A value counts as outdated after the integration's max age; it's fetched again
  when someone opens the game, optionally by the background scheduler (`manage.py run_scheduler`,
  runs under supervisord in Docker) in small batches, or by hand. If a source fails, cached values stay.
  A wrong automatic match can be fixed on the game page ("Change match"); that choice is kept.
  HowLongToBeat has **no official API**: shelvd uses its site's own search the way its pages do (a short-
  lived token from `/api/search/site/init`, sent as `x-auth-token` to `/api/search/site`; checked
  November 2026) and reads single games from their pages – it may break when the site changes, so
  it's off by default.
- **Cover search** (TheGamesDB, ScreenScraper) per release: candidates reach the browser only as
  encrypted tokens (ScreenScraper puts credentials into image URLs); previews and the chosen cover are
  fetched by the server from the source's own hosts over https, without redirects.
  When a game is added (scan, search), IGDB's cover, one picture for the whole game, goes on the work.
  The release gets box art from TheGamesDB of exactly that title and platform, its own region first;
  without one it shows the work's cover. ScreenScraper is too slow and quota-bound for that and stays
  in the manual search.

## Adding a source

Implement `MetadataSource`, `FactSource` or `CoverSource`
(`apps/providers/sources/base.py`) including `test()`, register it in `sources/registry.py`, describe
its fields in `services/integrations.DEFINITIONS` (and texts in `frontend/src/features/integrations/
locales`), and fake its HTTP in tests (`apps/providers/tests/fakes.py`). Images go through the server
(cover tokens), so no CSP change is needed. Good candidates: PriceCharting (paid barcodes, market values),
TMDB (films), Steam (play time of PC games).
