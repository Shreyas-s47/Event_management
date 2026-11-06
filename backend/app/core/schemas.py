from pydantic import BaseModel


class Page[Item](BaseModel):
    items: list[Item]
    total: int
    page: int
    page_size: int


class FieldError(BaseModel):
    field: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: list[FieldError]


class ErrorOut(BaseModel):
    error: ErrorDetail
    request_id: str | None
