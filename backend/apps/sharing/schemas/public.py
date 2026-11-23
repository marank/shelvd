from ninja import Schema


class PublicLibraryOut(Schema):
    name: str
    description: str
    owner: str
    item_count: int
