"""
Custom exception hierarchy.

All application exceptions inherit from AppException so they can be
caught by a single FastAPI exception handler. Each subclass carries an
HTTP status code and a machine-readable error code.
"""

from fastapi import status


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        detail: str = "An application error occurred.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "APP_ERROR",
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.detail)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource", identifier: str = ""):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(self, detail: str = "Could not validate credentials."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_ERROR",
        )


class AuthorizationError(AppException):
    """Insufficient permissions."""

    def __init__(self, detail: str = "You do not have permission to perform this action."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class ValidationError(AppException):
    """Input validation failed."""

    def __init__(self, detail: str = "Validation error."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
        )


class DocumentProcessingError(AppException):
    """Error during document extraction or processing."""

    def __init__(self, detail: str = "Failed to process the document."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="DOCUMENT_PROCESSING_ERROR",
        )


class AIServiceError(AppException):
    """Error from AI services (Gemini API, ChromaDB, etc.)."""

    def __init__(self, detail: str = "AI service encountered an error."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="AI_SERVICE_ERROR",
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
        )


class FileUploadError(AppException):
    """Error during file upload."""

    def __init__(self, detail: str = "File upload failed."):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="FILE_UPLOAD_ERROR",
        )
