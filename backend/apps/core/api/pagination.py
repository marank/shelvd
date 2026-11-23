from ninja import Schema


class Page[T](Schema):
    count: int
    items: list[T]
