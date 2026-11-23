"""Session auth for the SPA: csrf → login → me → logout (no trailing slashes)."""

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.utils.translation import gettext as _
from ninja import Router, Status
from ninja.errors import HttpError
from ninja.utils import check_csrf

from apps.core.api.errors import ErrorOut

from ..models import User
from ..schemas import LoginIn, RegisterIn, UserOut
from ..services import RegistrationError, register_user

router = Router(tags=["auth"])


def current_user(request: HttpRequest) -> User:
    """request.user typed as our model; only call on authenticated routes."""
    user = request.user
    if not isinstance(user, User):
        raise HttpError(401, _("Please sign in."))
    return user


def _require_csrf(request: HttpRequest) -> None:
    # auth=None routes skip Ninja's session-auth CSRF check, so do it here.
    if check_csrf(request) is not None:
        raise HttpError(403, _("CSRF verification failed."))


@router.get("csrf", auth=None, response={204: None})
def csrf(request: HttpRequest) -> Status[None]:
    get_token(request)  # sets the csrftoken cookie on the response
    return Status(204, None)


@router.post("login", auth=None, response={200: UserOut, 400: ErrorOut, 403: ErrorOut})
def login_view(request: HttpRequest, payload: LoginIn) -> Status[User | dict[str, str]]:
    _require_csrf(request)
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        return Status(400, {"detail": _("Invalid username or password.")})
    login(request, user)
    return Status(200, current_user(request))


@router.post("register", auth=None, response={201: UserOut, 400: ErrorOut, 403: ErrorOut})
def register(request: HttpRequest, payload: RegisterIn) -> Status[User | dict[str, str]]:
    _require_csrf(request)
    if not settings.REGISTRATION_ENABLED:
        return Status(403, {"detail": _("Registration is disabled.")})
    try:
        user = register_user(payload.username, payload.email, payload.password)
    except RegistrationError as exc:
        return Status(400, {"detail": exc.message})
    login(request, user, backend="apps.accounts.backends.CaseInsensitiveModelBackend")
    return Status(201, user)


@router.post("logout", response={204: None})
def logout_view(request: HttpRequest) -> Status[None]:
    logout(request)
    return Status(204, None)


@router.get("me", response=UserOut)
def me(request: HttpRequest) -> User:
    return current_user(request)
