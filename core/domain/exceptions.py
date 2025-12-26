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

    pass


class LicenseExpiredError(LicenseException):
    """Raised when a license has expired."""

    pass


class LicenseSuspendedError(LicenseException):
    """Raised when a license is suspended."""

    pass


class LicenseCancelledError(LicenseException):
    """Raised when a license is cancelled."""

    pass


class InvalidLicenseKeyError(LicenseException):
    """Raised when a license key is invalid."""

    pass


class SeatLimitExceededError(LicenseException):
    """Raised when license seat limit is exceeded."""

    pass


class BrandException(DomainException):
    """Base exception for brand-related errors."""

    pass


class BrandNotFoundError(BrandException):
    """Raised when a brand is not found."""

    pass


class InvalidAPIKeyError(BrandException):
    """Raised when an API key is invalid."""

    pass


class ActivationException(DomainException):
    """Base exception for activation-related errors."""

    pass


class ActivationNotFoundError(ActivationException):
    """Raised when an activation is not found."""

    pass


class InvalidInstanceIdentifierError(ActivationException):
    """Raised when an instance identifier is invalid."""

    pass


class InvalidLicenseStatusError(LicenseException):
    """Raised when a license operation is invalid for the current status."""

    pass
