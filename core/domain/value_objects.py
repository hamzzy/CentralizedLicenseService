"""
Value objects for the domain.

Value objects are immutable objects that are defined by their attributes
rather than their identity. They have no identity and are compared by value.
"""
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class ValueObject(ABC):
    """
    Base class for value objects.

    Value objects are immutable and compared by value.
    """

    def __eq__(self, other):
        """Compare value objects by their attributes."""
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self):
        """Make value objects hashable."""
        return hash(tuple(sorted(self.__dict__.items())))


@dataclass(frozen=True)
class Email(ValueObject):
    """Email value object with validation."""

    value: str

    def __post_init__(self):
        """Validate email format."""
        if not self.value or "@" not in self.value:
            raise ValueError(f"Invalid email address: {self.value}")

    def __str__(self) -> str:
        """Return email as string."""
        return self.value


@dataclass(frozen=True)
class BrandSlug(ValueObject):
    """Brand slug value object."""

    value: str

    def __post_init__(self):
        """Validate slug format."""
        if not self.value:
            raise ValueError("Brand slug cannot be empty")
        if not self.value.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid brand slug format: {self.value}")

    def __str__(self) -> str:
        """Return slug as string."""
        return self.value


@dataclass(frozen=True)
class ProductSlug(ValueObject):
    """Product slug value object."""

    value: str

    def __post_init__(self):
        """Validate slug format."""
        if not self.value:
            raise ValueError("Product slug cannot be empty")
        if not self.value.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid product slug format: {self.value}")

    def __str__(self) -> str:
        """Return slug as string."""
        return self.value


class LicenseStatus(Enum):
    """License status value object."""

    VALID = "valid"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    def __str__(self) -> str:
        """Return status as string."""
        return self.value


class InstanceType(Enum):
    """Instance type value object."""

    URL = "url"
    HOSTNAME = "hostname"
    MACHINE_ID = "machine_id"

    def __str__(self) -> str:
        """Return instance type as string."""
        return self.value


@dataclass(frozen=True)
class InstanceIdentifier(ValueObject):
    """Instance identifier value object."""

    value: str
    instance_type: InstanceType

    def __post_init__(self):
        """Validate instance identifier."""
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Instance identifier cannot be empty")
        if len(self.value) > 500:
            raise ValueError("Instance identifier too long")

    def __str__(self) -> str:
        """Return identifier as string."""
        return self.value
