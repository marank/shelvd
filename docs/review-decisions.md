# Review decisions

Points a code review raised and that were deliberately left as they are. A later review does not raise them again while the reason still holds. Remove an entry once it no longer applies.

- 2026-11-08 `catalog/selectors/terms.py:_uses` – Company counts use three `Count(distinct=True)` over left joins, which multiply rows for big publishers. Reason: no measured slowness. Revisit when: the companies page gets slow; then use `Subquery` counts.
