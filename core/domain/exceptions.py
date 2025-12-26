"""
Domain exceptions.

Domain exceptions represent business rule violations
and domain-specific error conditions.
"""


class DomainException(Exception):
    """Base exception for all domain exceptions."""

    def __init__(self, message: str, code: str = None):
        """
        Initialize domain exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class LicenseException(DomainException):
    """Base exception for license-related errors."""

    pass


class LicenseNotFoundError(LicenseException):
    """Raised when a license is not found."""

    def __init__(self, message: str = "License not found"):
        super().__init__(message, code="LICENSE_NOT_FOUND")


class LicenseExpiredError(LicenseException):
    """Raised when a license has expired."""

    def __init__(self, message: str = "License has expired"):
        super().__init__(message, code="LICENSE_EXPIRED")


class LicenseSuspendedError(LicenseException):
    """Raised when a license is suspended."""

    def __init__(self, message: str = "License is suspended"):
        super().__init__(message, code="LICENSE_SUSPENDED")


class LicenseCancelledError(LicenseException):
    """Raised when a license is cancelled."""

    def __init__(self, message: str = "License is cancelled"):
        super().__init__(message, code="LICENSE_CANCELLED")


class InvalidLicenseKeyError(LicenseException):
    """Raised when a license key is invalid."""

    def __init__(self, message: str = "Invalid license key"):
        super().__init__(message, code="INVALID_LICENSE_KEY")


class SeatLimitExceededError(LicenseException):
    """Raised when license seat limit is exceeded."""

    def __init__(self, message: str = "License seat limit exceeded"):
        super().__init__(message, code="SEAT_LIMIT_EXCEEDED")


class BrandException(DomainException):
    """Base exception for brand-related errors."""

    pass


class BrandNotFoundError(BrandException):
    """Raised when a brand is not found."""

    def __init__(self, message: str = "Brand not found"):
        super().__init__(message, code="BRAND_NOT_FOUND")


class InvalidAPIKeyError(BrandException):
    """Raised when an API key is invalid."""

    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, code="INVALID_API_KEY")


class ActivationException(DomainException):
    """Base exception for activation-related errors."""

    pass


class ActivationNotFoundError(ActivationException):
    """Raised when an activation is not found."""

    def __init__(self, message: str = "Activation not found"):
        super().__init__(message, code="ACTIVATION_NOT_FOUND")


class InvalidInstanceIdentifierError(ActivationException):
    """Raised when an instance identifier is invalid."""

    def __init__(self, message: str = "Invalid instance identifier"):
        super().__init__(message, code="INVALID_INSTANCE_IDENTIFIER")


class InvalidLicenseStatusError(LicenseException):
    """Raised when a license operation is invalid for the current status."""

    def __init__(self, message: str = "Invalid license status"):
        super().__init__(message, code="INVALID_LICENSE_STATUS")
