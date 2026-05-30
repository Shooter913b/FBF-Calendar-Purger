class FBFError(Exception):
    """Base error for FBF purge library."""


class CanvasAuthError(FBFError):
    """Canvas returned 401 or 403."""


class CanvasNotFoundError(FBFError):
    """Canvas returned 404."""


class CanvasAPIError(FBFError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)
