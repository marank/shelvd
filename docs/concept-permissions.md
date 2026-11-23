# Concept: who may change what (catalog, copies, shared libraries)

Status: implemented (2026-11-11); the rules are in `AGENTS.md`. Open: the clean-up of the seven
copy covers from before (step 4).

## Principles

1. **The catalog is the local source of truth** for games (`Work`) and releases (`Release`),
   and for platforms, companies, genres, series and barcodes. Only **admins** (`is_staff`)
   change it.
2. **Copies (`Item`) belong to a library** and may differ from the catalog wherever their
   library wants. A difference is stored on the copy, never copied from the catalog: an empty
   override means "as the release", so catalog corrections reach every copy that doesn't differ,
   and *reset* simply clears the override.
3. **Library roles stay as they are**: owner, editor, viewer. Overrides are per copy and the
   same for all members ("user-level" means library-level).
4. Everyone may still **bring games in**: taking a game from IGDB is source data and needs no
   review. What a person types or decides themselves – a game entered by hand, a barcode
   assigned to a release – lands in the catalog as **unreviewed** until an admin approves it.
5. The backend enforces every rule; the frontend hides what you can't do and guards routes, so
   nobody sees a button that ends in "not allowed".

## Roles

| Role | Where | May |
|---|---|---|
| Admin | `User.is_staff` | everything in the catalog, review queue, integrations |
| Owner | `Library.owner` | the library: settings, members, public link, delete; plus all of editor |
| Editor | `LibraryMember.role=editor` | copies, overrides, locations, people, loans, imports into this library |
| Viewer | `LibraryMember.role=viewer` | read the library; own views, lists, play time, watchlist |
| Any user | logged in | own libraries, own lists, own watchlist |

## Catalog

### Who writes what

| Action | Today | New |
|---|---|---|
| Edit game / release, covers, barcodes on the edit page | any user | admin |
| Merge games, move releases | any user | admin |
| Metadata match ("Abgleich") with IGDB/Wikipedia | any user | admin |
| Cover search for a release | any user | admin |
| Terms (rename, merge, delete, image, description) | any user | admin |
| Platforms (create, edit, delete, icon) | any user | admin |
| Fact match (pin/unpin HLTB, OpenCritic), forced refresh | any user | admin |
| Automatic fact refresh on opening a game | any user | unchanged (cache, no decision) |
| Release date from Upcoming (catalog PATCH) | entry owner | admin; others see the date read-only |
| Take a game from IGDB (scan, search) | any user | any library editor – **reviewed** (source data); TheGamesDB cover as today |
| Enter a game yourself (`/releases/new`) | any user | any library editor – creates **unreviewed** work + release |
| Assign a barcode to a release (scan, search, manual form) | any user | any library editor – creates an **unreviewed** barcode |
| Import from another tool (importer add-on) | library editor, writes catalog freely | library editor; new works/releases/barcodes **unreviewed**; reviewed entries are never changed (see below) |
| Play time "this is the game" | user, sets a global link for everyone | user, for their own records only; global title links only by admins |

### Unreviewed entries

- `Work`, `Release` and `Barcode` get `review_status` (`pending` | `approved`), `created_by`,
  `reviewed_by`, `reviewed_at`. Existing rows become `approved` in the migration.
- Unreviewed entries are **usable right away** by everyone (search, scan, copies), marked with an
  "Ungeprüft" badge. A pending barcode answers scans like a confirmed one, with the badge.
- The person who created a pending entry may still edit it until it is reviewed (typos), nobody
  else except admins.
- **Review queue** `/catalog/review` (admins, sidebar entry with a count): pending works,
  releases and barcodes with who/when and the copies using them. Actions: *approve*, *edit*
  (existing edit pages), *merge into an existing game / move to an existing release* (existing
  merge/move tools, which re-point copies), *remove barcode*. Removing a pending release that
  has copies is only possible by merging/moving it.
- **Importers** never overwrite reviewed entries. Values an import has for reviewed entries
  that differ are not lost: title and cover become copy overrides when they differ – see
  *Decisions*.

## Copies and overrides

Overridable on a copy (empty = as the release): **title, cover, edition, region, release date
(with precision)**. Not overridable: platform and game – a copy on another platform is another
release; editors move a copy to another release instead (`release_id`, already possible).

- Model: `Item.title_override` and `cover_override` stay; new `edition_override`,
  `region_override`, `release_date_override` + `release_precision_override` (+ `_end`), all
  nullable/blank.
- Effective values as `Item` properties (`display_title`, `cover_url` exist; add `edition`,
  `region`, `release_date`, `sort_date`, `is_released`). Grouping, sorting and conditions
  already work on loaded items (`selectors/grouping|sorting|conditions`), so `release.edition`,
  `release.region`, `release.date`, `release.year`, `release.decade` read the effective value
  for copies. Field keys stay the same; catalog pages keep showing catalog values.
- API: `ItemOut` returns the effective values plus `overrides` (which fields differ, with the
  catalog value) so the UI can mark them. `ItemPatch` accepts the overrides; `null` resets one;
  `POST /items/{id}/reset` resets all.
- UI: the copy's edit page gets a section **"Abweichungen vom Katalog"**: each overridable field
  shows the catalog value beside it, "Auf Ausgabe zurücksetzen" per field and "Alle
  zurücksetzen". Copy pages and the explorer mark differing values (small dot + tooltip
  "abweichend von der Ausgabe: …"). Cover search on a copy keeps setting the copy's cover.
- Public pages show effective values (as today for title and cover).

## Shared libraries (what viewers see and may do)

Tested on 2026-11-11 with the API as the viewer `claude-test` (all writes rolled back):

| Area | Today | New |
|---|---|---|
| Catalog edit, merge, move, delete term, platforms | **allowed** (200) | admin only |
| Enter a game yourself, assign barcode | **allowed** (201) | editor of some library, unreviewed |
| Copies, locations, people, loans, library settings, members, public link | 403 ✓ | unchanged |
| Read people incl. e-mail and notes | allowed | names only |
| Read loans | allowed | library setting: hidden or status only |
| Read purchase price, current value, total value | allowed | hidden |
| Own views (Overviews) in the shared library | allowed | unchanged |
| Lists incl. copies of the shared library, public list link | allowed | unchanged (lists show release + note only) |
| Put own Upcoming entry into the shared library | allowed (viewer) | editor; members see game and status, not price/shop/notes of others |
| Integrations | 403 ✓ | unchanged |
| Create own library | allowed | unchanged |

Frontend findings to fix (from the audit):
- Catalog actions without any check: game edit/merge/match (`WorkDetail`), release edit/move/
  cover search (`ReleaseView`, `ReleaseGrid` ⋮), terms, platforms, fact match, release date
  link in Upcoming. → shown only to admins.
- No route guards beyond login. → `meta.requires: 'admin' | 'editor'`; the router checks admin
  from `auth.user.is_staff`, editor from the route's library/copy; otherwise a "Keine
  Berechtigung" page instead of a form that fails on save. Covers `work-edit`, `work-merge`,
  `release-edit`, `release-move`, `release-new`, cover/metadata/fact match, term and platform
  edit/merge, `integration-edit`, `item-edit`, `item-lend`, imports.
- "Add game" in the topbar is hidden for viewers – fine; on Upcoming adding is personal and
  should not depend on the current library's role.

## Explorer: a click opens the copy

The items of a library view are copies. Clicking one opens **`/items/<id>`** instead of the game
page (`ExplorerView.openItem`). With the detail column open on desktop a click keeps selecting
(the column already shows the copy and links to it). The copy page links up to release and game
as today.

## Decisions (agreed 2026-11-11)

1. **What viewers may read:** everything except people's contact details (e-mail, notes) and
   money (purchase price, current value, total value). Who owns a copy (the owner's name) stays
   visible. Loans are a per-library setting for viewers: **hidden** or **status only** (lent or
   not, no borrower, no dates). Editors and owners see everything.
2. **Imported values for reviewed entries:** differing title/cover become copy overrides,
   everything else is dropped.
3. **Play time:** only admins set global title links; users confirm their own records only.
4. **Who may enter games / assign barcodes:** anyone who is editor or owner of at least one
   library.

## Steps

1. Backend permissions: `require_admin` helper; catalog, terms, platforms, metadata, cover,
   facts-match and release-date routes admin-only; tests per route (viewer 403, admin 200).
2. Review status: model fields + migration (existing → approved), creation paths set
   `pending`/`created_by`, creator may edit own pending; review queue API and page; badge.
3. Importers: never touch reviewed entries; new entries pending (+ decision 2).
4. Overrides: fields, effective properties, API, grouping/sorting/conditions, copy edit section
   with reset, markers; data clean-up of the 7 current copy covers (platform covers → releases,
   IGDB covers → games, overrides cleared).
5. Frontend gating: hide catalog actions for non-admins, route guards with a no-permission
   page, Upcoming independent of library role.
6. Viewer read rules (decision 1), Upcoming target library needs editor, play time global link
   (decision 3).
7. Explorer click → copy page.
8. Update `AGENTS.md` (domain rules, roles) and `docs/data-sources.md`.
