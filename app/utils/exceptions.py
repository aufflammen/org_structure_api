"""Application-specific errors mapped to HTTP responses."""


class DomainBadRequestError400(Exception):
    """Invalid input; maps to HTTP 400."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DomainNotFoundError404(Exception):
    """Missing entity; maps to HTTP 404."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DomainConflictError409(Exception):
    """Maps to HTTP 409."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
