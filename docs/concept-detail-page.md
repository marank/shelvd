# Concept: one page for a game in your collection

Status: agreed (2026-11-11); built as one game page with three focuses (2026-11-12, see the end).

## Idea

People think "my #BLUD", not "a copy of a release of a work". The three levels stay in the data
model, in views (field chooser, sorting, filters) and in catalog upkeep for admins – the page a
person opens for a game hides them.

## The page (`/items/<id>`, later also for games without a copy)

From top to bottom:

1. **Back** (no level trail) and the ⋮ menu (copy actions; catalog upkeep for admins).
2. **Head**: the cover of the copy you're looking at; the title with the release number beside
   it in a muted colour (`#129`, follows the selected copy, absent without one); the game's
   description, clamped, with "Mehr lesen"; a few figures: play time from HowLongToBeat, critic
   score, and what add-ons add (e.g. your own play time). No tags under the title.
3. **In deiner Sammlung · n**: all copies of the game in this library as a row of covers that
   wraps (any number), each labelled briefly ("Switch · PAL", "verliehen"). The selected one is
   outlined; clicking another opens that copy. Below, over the full width, the selected copy:
   heading ("Switch · PAL"), its own facts (place, condition, acquired, price, value, owner,
   play status, tags, notes, current loan) and actions (edit, lend / give back, add to list).
   Differences from the release are marked ("Eigene Werte").
4. **Details**: one labelled field list without level headings – platform, released, genres,
   series, developers, publisher, region, edition, barcode, age rating, product code. Term
   values link to their pages.
5. **Weiterführend**: internal links ("Alle Ausgaben dieses Spiels" → game page, "Diese Ausgabe
   im Katalog" → release page) and external ones where we know the address (HowLongToBeat,
   OpenCritic now; IGDB once its page URL is stored).

Editing always means your copy (incl. its own values); catalog editing is in the ⋮ menu for
admins only.

## Steps

1. The copy page as above.
2. The game page in the same layout for games without a copy in this library (Upcoming, search,
   other releases): instead of the copy block "Nicht in deiner Sammlung" with watch / add. The
   release page stays for catalog upkeep.
3. External links: store IGDB's page URL on import and match; TheGamesDB only once its game id
   is stored with a cover.


## One page, three focuses (2026-11-12)

Steps 1 and 2 became one page: the game, its releases and your copies, at `/items/<id>`,
`/releases/<id>` and `/works/<id>` alike (`features/game`). The address only sets the focus:

- **Copy**: its cover, no kicker, its title and release number; „Dieses Exemplar“ first.
- **Release**: its cover, „Eine Ausgabe von <Spiel>“; add a copy of it or watch it.
- **Game**: its own cover (else one of your copies'), „Spiel · n Ausgaben“ with the platforms;
  no release section, no publisher – pick a release in „Alle Ausgaben“.

The sections are the same everywhere and in the same order – Dieses Exemplar, In deiner
Sammlung, Diese Ausgabe, Das Spiel, Alle Ausgaben, Mehr aus der Reihe, Weiterführend – and
each folds in and out; what someone folds is remembered per focus in the browser. On a copy's
page „Alle Ausgaben“ starts folded. „Das Spiel“ holds what IGDB says about how it's played:
modes, perspective, languages (voice / subtitles / menus) – translated where we know the
names, else as IGDB gives them. „Alle Ausgaben“ is a timeline (a row per platform, a dot per
release: filled when you have it, ringed for the one in focus) above a list.

No tabs: they would hide information behind clicks, and the folding sections already let
everyone keep what they don't need out of the way.
