"""What an add-on registers with the providers: integrations, jobs, testable sources."""

from collections.abc import Iterator

import pytest

from apps.providers.services import integrations, scheduler
from apps.providers.services.integrations import DEFINITIONS, Definition
from apps.providers.sources import registry


@pytest.fixture
def clean() -> Iterator[None]:
    definitions, jobs, testable = (
        dict(DEFINITIONS),
        list(scheduler.JOBS),
        dict(registry.EXTRA_TESTABLE),
    )
    yield
    DEFINITIONS.clear()
    DEFINITIONS.update(definitions)
    scheduler.JOBS[:] = jobs
    registry.EXTRA_TESTABLE.clear()
    registry.EXTRA_TESTABLE.update(testable)


class FakeSource:
    def test(self) -> str:
        return "OK"


@pytest.mark.django_db
@pytest.mark.usefixtures("clean")
def test_registered_integration_job_and_test() -> None:
    integrations.register(Definition("demo", "Demo", "playtime", "https://example.com"))
    assert integrations.definition("demo").name == "Demo"
    assert integrations.config("demo").active is False  # off until an admin switches it on

    def job() -> dict[str, int]:
        return {"demo": 3}

    scheduler.register(job)
    scheduler.register(job)  # once only
    assert scheduler.JOBS.count(job) == 1
    assert scheduler.run_due()["demo"] == 3

    registry.register_testable("demo", FakeSource)
    assert registry.testable("demo").test() == "OK"
