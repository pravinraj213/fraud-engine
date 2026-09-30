class NotFoundError(Exception):
    """The requested record does not exist (HTTP 404)."""


class ConflictError(Exception):
    """The request conflicts with the record's current state (HTTP 409)."""
