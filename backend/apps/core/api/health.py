from django.http import HttpRequest
from ninja import Router, Schema

router = Router(tags=["health"])


class HealthOut(Schema):
    status: str


@router.get("", auth=None, response=HealthOut)
def health(request: HttpRequest) -> HealthOut:
    return HealthOut(status="ok")
