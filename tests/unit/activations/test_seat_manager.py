"""
Unit tests for SeatManager domain service.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from activations.domain.services import SeatManager
from core.domain.value_objects import LicenseStatus
from licenses.domain.license import License


@pytest.mark.asyncio
class TestSeatManager:
    """Tests for SeatManager service."""

    async def test_count_active_seats(self, activation_repository, db_license):
        """Test counting active seats."""
        # Create activations
        from activations.domain.activation import Activation
        from core.domain.value_objects import InstanceType

        activation1 = Activation.create(
            license_id=db_license.id,
            instance_identifier="https://site1.com",
            instance_type=InstanceType.URL,
        )
        activation2 = Activation.create(
            license_id=db_license.id,
            instance_identifier="https://site2.com",
            instance_type=InstanceType.URL,
        )

        await activation_repository.save(activation1)
        await activation_repository.save(activation2)

        count = await SeatManager.count_active_seats(db_license.id, activation_repository)

        assert count == 2

    async def test_has_available_seats(self, activation_repository, db_license):
        """Test checking available seats."""
        # License has seat_limit=5, no activations yet
        has_seats = await SeatManager.has_available_seats(db_license, activation_repository)

        assert has_seats is True

    async def test_has_available_seats_full(self, activation_repository, db_license):
        """Test checking available seats when full."""
        from activations.domain.activation import Activation
        from core.domain.value_objects import InstanceType

        # Create 5 activations (seat_limit=5)
        for i in range(5):
            activation = Activation.create(
                license_id=db_license.id,
                instance_identifier=f"https://site{i}.com",
                instance_type=InstanceType.URL,
            )
            await activation_repository.save(activation)

        has_seats = await SeatManager.has_available_seats(db_license, activation_repository)

        assert has_seats is False

    async def test_can_activate_valid_license(self, activation_repository, db_license):
        """Test can_activate for valid license."""
        can_activate, error = await SeatManager.can_activate(
            db_license,
            "https://newsite.com",
            activation_repository,
        )

        assert can_activate is True
        assert error is None

    async def test_can_activate_duplicate_instance(self, activation_repository, db_license):
        """Test can_activate for duplicate instance."""
        from activations.domain.activation import Activation
        from core.domain.value_objects import InstanceType

        # Create existing activation
        activation = Activation.create(
            license_id=db_license.id,
            instance_identifier="https://existing.com",
            instance_type=InstanceType.URL,
        )
        await activation_repository.save(activation)

        can_activate, error = await SeatManager.can_activate(
            db_license,
            "https://existing.com",
            activation_repository,
        )

        assert can_activate is False
        assert "already activated" in error.lower()

    async def test_can_activate_seat_limit_exceeded(self, activation_repository, db_license):
        """Test can_activate when seat limit exceeded."""
        from activations.domain.activation import Activation
        from core.domain.value_objects import InstanceType

        # Fill all seats
        for i in range(5):  # seat_limit=5
            activation = Activation.create(
                license_id=db_license.id,
                instance_identifier=f"https://site{i}.com",
                instance_type=InstanceType.URL,
            )
            await activation_repository.save(activation)

        can_activate, error = await SeatManager.can_activate(
            db_license,
            "https://newsite.com",
            activation_repository,
        )

        assert can_activate is False
        assert "exceeded" in error.lower()
