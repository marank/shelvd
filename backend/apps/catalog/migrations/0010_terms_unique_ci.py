"""Companies and genres are unique regardless of case, like series: "Level-5" and
"LEVEL-5" are one company. Existing duplicates are merged into the most used spelling."""

from collections import defaultdict
from typing import Any

from django.db import migrations, models
from django.db.models.functions import Lower


def merge_duplicates(apps: Any, schema_editor: Any) -> None:
    Company = apps.get_model("catalog", "Company")
    Genre = apps.get_model("catalog", "Genre")
    Release = apps.get_model("catalog", "Release")
    Work = apps.get_model("catalog", "Work")
    for model, through, field in (
        (Company, Work.developers.through, "company"),
        (Genre, Work.genres.through, "genre"),
    ):
        groups: dict[str, list[Any]] = defaultdict(list)
        for term in model.objects.order_by("name"):
            groups[term.name.lower()].append(term)
        for terms in groups.values():
            if len(terms) < 2:
                continue

            def uses(term: Any) -> int:
                count = through.objects.filter(**{field: term}).count()
                if model is Company:
                    count += Release.objects.filter(publisher=term).count()
                return int(count)

            keep, *others = sorted(terms, key=lambda t: (-uses(t), t.name))
            for other in others:
                if model is Company:
                    Release.objects.filter(publisher=other).update(publisher=keep)
                linked = through.objects.filter(**{field: keep}).values("work_id")
                through.objects.filter(**{field: other}, work_id__in=linked).delete()
                through.objects.filter(**{field: other}).update(**{field: keep})
                keep.external_ids = {**other.external_ids, **keep.external_ids}
                other.delete()
            keep.save()


class Migration(migrations.Migration):
    dependencies = [("catalog", "0009_series")]

    operations = [
        migrations.RunPython(merge_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="company",
            constraint=models.UniqueConstraint(Lower("name"), name="company_name_unique_ci"),
        ),
        migrations.AddConstraint(
            model_name="genre",
            constraint=models.UniqueConstraint(Lower("name"), name="genre_name_unique_ci"),
        ),
    ]
