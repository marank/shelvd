from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from config import env


def test_load_dotenv_does_not_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("# comment\nSHELVD_A=1\nexport SHELVD_B='two'\nSHELVD_C=from-file\nbroken\n")
    monkeypatch.setenv("SHELVD_C", "from-env")
    for key in ("SHELVD_A", "SHELVD_B"):
        monkeypatch.delenv(key, raising=False)
    env.load_dotenv(tmp_path / "missing", dotenv)
    import os

    assert os.environ["SHELVD_A"] == "1"
    assert os.environ["SHELVD_B"] == "two"
    assert os.environ["SHELVD_C"] == "from-env"
    monkeypatch.delenv("SHELVD_A")
    monkeypatch.delenv("SHELVD_B")


def test_env_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHELVD_BOOL", "yes")
    monkeypatch.setenv("SHELVD_INT", "7")
    monkeypatch.setenv("SHELVD_LIST", "a, b,,c")
    assert env.env_bool("SHELVD_BOOL") is True
    assert env.env_bool("SHELVD_UNSET", True) is True
    assert env.env_int("SHELVD_INT", 1) == 7
    assert env.env_int("SHELVD_UNSET", 3) == 3
    assert env.env_list("SHELVD_LIST") == ["a", "b", "c"]
    assert env.env_list("SHELVD_UNSET", ["x"]) == ["x"]
    assert env.env_str("SHELVD_UNSET", "d") == "d"
    monkeypatch.setenv("SHELVD_BOOL", "maybe")
    with pytest.raises(ImproperlyConfigured):
        env.env_bool("SHELVD_BOOL")
    monkeypatch.setenv("SHELVD_BOOL", "off")
    assert env.env_bool("SHELVD_BOOL", True) is False
    monkeypatch.setenv("SHELVD_INT", "x")
    with pytest.raises(ImproperlyConfigured):
        env.env_int("SHELVD_INT", 1)
    with pytest.raises(ImproperlyConfigured):
        env.env_str("SHELVD_UNSET")


def test_parse_app_urls() -> None:
    urls = env.parse_app_urls(["https://games.example.com", "http://localhost:8080"])
    assert [u.origin for u in urls] == ["https://games.example.com", "http://localhost:8080"]
    assert urls[0].hostname == "games.example.com"
    with pytest.raises(ImproperlyConfigured):
        env.parse_app_urls(["ftp://x"])
    with pytest.raises(ImproperlyConfigured):
        env.parse_app_urls([])


def test_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "change-me")
    assert env.secret_key(True).startswith("django-insecure-dev-only-")
    with pytest.raises(ImproperlyConfigured):
        env.secret_key(False)
    monkeypatch.setenv("SECRET_KEY", "k" * 50)
    assert env.secret_key(False) == "k" * 50
