"""Admins set up external services here (instead of .env)."""

from django.http import HttpRequest
from django.utils.translation import gettext as _
from ninja import Router
from ninja.errors import HttpError

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..schemas import IntegrationFieldOut, IntegrationOut, IntegrationPatch, TestOut
from ..services.integrations import DEFINITIONS, Config, config, mask, record_error, record_ok
from ..services.integrations import save as save_config
from ..sources import ProviderError
from ..sources.registry import testable

router = Router(tags=["integrations"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut}


def require_staff(request: HttpRequest) -> None:
    if not current_user(request).is_staff:
        raise HttpError(403, _("Only admins can change integrations."))


def integration_out(cfg: Config) -> IntegrationOut:
    d = DEFINITIONS[cfg.key]
    row = cfg.row
    fields = []
    for f in d.fields:
        if f.secret:
            secret = cfg.secrets.get(f.name, "")
            fields.append(
                IntegrationFieldOut(
                    name=f.name,
                    type=f.type,
                    secret=True,
                    required=f.required,
                    has_value=bool(secret),
                    masked=mask(secret) if secret else "",
                )
            )
        else:
            value = cfg.options.get(f.name)
            fields.append(
                IntegrationFieldOut(
                    name=f.name,
                    type=f.type,
                    secret=False,
                    required=f.required,
                    value=value,
                    has_value=value not in (None, ""),
                )
            )
    return IntegrationOut(
        key=d.key,
        name=d.name,
        kind=d.kind,
        url=d.url,
        unofficial=d.unofficial,
        refreshes=d.refreshes,
        enabled=cfg.enabled,
        active=cfg.active,
        fields=fields,
        last_ok_at=row.last_ok_at if row else None,
        last_error=row.last_error if row else "",
        last_error_at=row.last_error_at if row else None,
        last_run_at=row.last_run_at if row else None,
    )


@router.get("", response={200: list[IntegrationOut], **ERRORS})
def list_integrations(request: HttpRequest) -> list[IntegrationOut]:
    require_staff(request)
    return [integration_out(config(key)) for key in DEFINITIONS]


@router.patch("{key}", response={200: IntegrationOut, **ERRORS})
def update_integration(request: HttpRequest, key: str, payload: IntegrationPatch) -> IntegrationOut:
    require_staff(request)
    return integration_out(
        save_config(key, enabled=payload.enabled, options=payload.options, secrets=payload.secrets)
    )


@router.post("{key}/test", response={200: TestOut, **ERRORS})
def test_integration(request: HttpRequest, key: str) -> TestOut:
    """Try the saved settings (also while switched off)."""
    require_staff(request)
    if key not in DEFINITIONS:
        raise HttpError(404, _("Unknown integration."))
    if not config(key).complete:
        return TestOut(ok=False, message=_("Fill in all required fields first."))
    try:
        message = testable(key).test()
    except ProviderError as exc:
        record_error(key, str(exc))
        return TestOut(ok=False, message=str(exc))
    record_ok(key)
    return TestOut(ok=True, message=message)
