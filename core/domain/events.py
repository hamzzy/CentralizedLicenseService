"""
Domain events base classes and infrastructure.

Domain events represent something that happened in the domain.
They are used for decoupling modules and enabling event-driven architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    Base class for all domain events.

    Domain events are immutable value objects that represent
    something that happened in the domain.
    """

    event_id: UUID
    occurred_at: datetime
    aggregate_id: str
    event_type: str

    def __init_subclass__(cls, **kwargs):
        """Automatically set event_type for subclasses."""
        super().__init_subclass__(**kwargs)
        cls.event_type = cls.__name__

    def __post_init__(self):
        """Set default values if not provided."""
        object.__setattr__(self, "event_id", getattr(self, "event_id", uuid4()))
        object.__setattr__(self, "occurred_at", getattr(self, "occurred_at", datetime.utcnow()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "event_type": self.event_type,
        }


class EventHandler(ABC):
    """
    Base class for event handlers.

    Event handlers process domain events asynchronously.
    """

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Handle a domain event.

        Args:
            event: The domain event to handle
        """
        pass


class EventBus(ABC):
    """
    Abstract event bus for publishing and subscribing to domain events.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event.

        Args:
            event: The domain event to publish
        """
        pass

    @abstractmethod
    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        """
        Subscribe to a domain event type.

        Args:
            event_type: The type of event to subscribe to
            handler: The handler to call when event is published
        """
        pass
