from typing import Any


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: Any = None):
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or []


def conflict(message: str) -> DomainError:
    return DomainError(409, "conflict", message)
