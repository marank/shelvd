import datetime
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import Any

import httpx
import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.catalog.models import Franchise, Platform, Release, Work
from apps.providers.services import bulk_match
from apps.providers.services.integrations import save
from apps.providers.services.metadata import Change, Value
from apps.providers.sources import ProviderError
from apps.providers.sources.igdb import IGDBSource, saved_answers

from .fakes import IGDB_GAME, host, response, router


def change(field: str, kind: str, current: Value, proposed: Value, **kw: Any) -> Change:
    return Change(f"work.{field}", field, kind, current, proposed, **kw)


def day(text: str) -> Value:
    return Value(date=datetime.date.fromisoformat(text))


def test_takes_only_what_is_missing_or_clearly_wrong() -> None:
    assert bulk_match.takes(change("summary", "fill", Value(), Value(text="x")))
    assert bulk_match.takes(change("release_date", "precise", day("2020-01-01"), day("2020-03-02")))
    assert not bulk_match.takes(change("summary", "differs", Value(text="a"), Value(text="b")))
    assert not bulk_match.takes(change("title", "differs", Value(text="a"), Value(text="b")))
    # Pictures are chosen by hand.
    assert not bulk_match.takes(change("cover", "fill", Value(), Value(image="u"), cover_url="u"))
    first = "first_release_date"
    assert bulk_match.takes(change(first, "differs", day("2021-03-05"), day("2017-10-27")))
    assert not bulk_match.takes(change(first, "differs", day("2017-03-05"), day("2017-10-27")))
    # 1 June stands for "that year".
    assert bulk_match.takes(change(first, "differs", day("2017-06-01"), day("2017-10-27")))
    assert not bulk_match.takes(change(first, "differs", day("2016-06-01"), day("2017-10-27")))
    assert not bulk_match.takes(change(first, "differs", day("2016-06-01"), Value()))


def run(*args: str) -> str:
    out = StringIO()
    call_command("match_metadata", *args, stdout=out)
    return out.getvalue()


@pytest.fixture
def answers(tmp_path: Path) -> Any:
    with override_settings(DATA_DIR=tmp_path):
        yield tmp_path / "answers" / "igdb"


def test_dry_run_then_apply(
    igdb: list[str],
    answers: Path,
    make_release: Callable[..., Release],
    switch: Platform,
    nds: Platform,
) -> None:
    odyssey = make_release("Super Mario Odyssey", switch)
    elsewhere = make_release("Super Mario Odyssey", nds)
    unknown = make_release("Nothing Like It", switch)
    linked = make_release("Odyssey, linked", switch)
    linked.work.external_ids = {"igdb": "26758"}
    linked.work.save()
    toy = Work.objects.create(title="Mario amiibo", media_type="toy")

    report = run()
    assert "[matched] Super Mario Odyssey  ⇒  Super Mario Odyssey (26758)" in report
    assert "    + summary: – → Cappy!" in report
    assert "    + Switch publisher: – → Nintendo" in report
    assert "    · cover: – → image" in report  # never taken
    assert "same title, but not on our platforms" in report
    assert "[none] Nothing Like It" in report
    assert "[linked] Odyssey, linked" in report
    assert toy.title not in report
    assert "would be applied" in report
    odyssey.work.refresh_from_db()
    assert (odyssey.work.external_ids, odyssey.work.summary) == ({}, "")

    # The real run answers from the saved files: IGDB isn't asked again.
    asked = len(igdb)
    assert any(answers.iterdir())
    assert "changes applied" in run("--apply")
    assert len(igdb) == asked
    odyssey.work.refresh_from_db()
    assert odyssey.work.external_ids == {"igdb": "26758"}
    assert odyssey.work.summary == "Cappy!"
    assert not odyssey.work.cover
    elsewhere.work.refresh_from_db()
    unknown.work.refresh_from_db()
    assert elsewhere.work.external_ids == {} == unknown.work.external_ids

    # One work; --fresh asks the source again.
    report = run("--work", str(unknown.work_id), "--fresh")
    assert len(igdb) > asked
    assert report.splitlines()[0] == "[none] Nothing Like It"


def test_unsure_with_several_games(
    db: None,
    answers: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_release: Callable[..., Release],
    switch: Platform,
) -> None:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    remake = {**IGDB_GAME, "id": 1}
    monkeypatch.setattr(
        "httpx.post",
        router(
            {
                "https://id.twitch.tv": lambda *a, **k: response(json={"access_token": "t"}),
                "https://api.igdb.com": lambda *a, **k: response(json=[IGDB_GAME, remake]),
            }
        ),
    )
    make_release("Super Mario Odyssey", switch)
    assert "several games of that title: 1, 26758" in run()


def test_source_errors(
    db: None,
    answers: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_release: Callable[..., Release],
    switch: Platform,
) -> None:
    with pytest.raises(CommandError):
        run()
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    monkeypatch.setattr("httpx.post", router({}))
    make_release("Super Mario Odyssey", switch)
    assert "[failed] Super Mario Odyssey" in run()


def test_rate_limit_waits_and_tries_again(
    db: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    answers = iter([response(429, json=[]), response(json=[IGDB_GAME])])

    def post(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        if host(url) == "id.twitch.tv":
            return response(json={"access_token": "t"})
        return next(answers)

    waits: list[float] = []
    monkeypatch.setattr("httpx.post", post)
    monkeypatch.setattr("time.sleep", waits.append)
    with saved_answers(tmp_path):
        assert IGDBSource().search("Mario")[0].title == "Super Mario Odyssey"
    assert waits == [1.0]

    monkeypatch.setattr(
        "httpx.post", lambda url, *a, **k: post(url) if "twitch" in url else response(429, json=[])
    )
    with pytest.raises(ProviderError):
        IGDBSource().search("Luigi")
    assert len(waits) == 5


def test_franchises_filled(
    igdb: list[str],
    answers: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_release: Callable[..., Release],
    switch: Platform,
) -> None:
    game = {**IGDB_GAME, "franchises": [{"name": "Mario"}]}
    monkeypatch.setattr(
        "httpx.post",
        router(
            {
                "https://id.twitch.tv": lambda *a, **k: response(json={"access_token": "t"}),
                "https://api.igdb.com": lambda *a, **k: response(json=[game]),
            }
        ),
    )
    release = make_release("Super Mario Odyssey", switch)
    run("--apply")
    assert list(release.work.franchises.all()) == [Franchise.objects.get(name="Mario")]


def test_names_compare_without_accents() -> None:
    from apps.providers.sources.names import normalize

    assert normalize("Pokémon Sword") == normalize("Pokemon: Sword") == "pokemonsword"
