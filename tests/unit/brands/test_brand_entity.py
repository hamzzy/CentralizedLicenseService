"""
Unit tests for Brand domain entity.
"""

import uuid

import pytest

from brands.domain.brand import Brand
from core.domain.value_objects import BrandSlug


class TestBrandEntity:
    """Tests for Brand domain entity."""

    def test_create_brand(self):
        """Test creating a brand entity."""
        brand = Brand.create(name="RankMath", slug="rankmath", prefix="RM")

        assert brand.name == "RankMath"
        assert brand.slug.value == "rankmath"
        assert brand.prefix == "RM"
        assert isinstance(brand.id, uuid.UUID)
        assert brand.created_at is not None

    def test_create_brand_with_id(self):
        """Test creating a brand with specific ID."""
        brand_id = uuid.uuid4()
        brand = Brand.create(
            name="RankMath",
            slug="rankmath",
            prefix="RM",
            brand_id=brand_id,
        )

        assert brand.id == brand_id

    def test_brand_prefix_uppercase(self):
        """Test brand prefix is converted to uppercase."""
        brand = Brand.create(name="RankMath", slug="rankmath", prefix="rm")
        assert brand.prefix == "RM"

    def test_update_name(self):
        """Test updating brand name."""
        brand = Brand.create(name="RankMath", slug="rankmath", prefix="RM")
        updated = brand.update_name("RankMath Pro")

        assert updated.name == "RankMath Pro"
        assert updated.id == brand.id
        assert updated.slug == brand.slug
        assert updated.updated_at > brand.updated_at

    def test_invalid_name_empty(self):
        """Test invalid empty name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Brand.create(name="", slug="test", prefix="T")

    def test_invalid_name_too_long(self):
        """Test invalid name too long."""
        long_name = "x" * 256
        with pytest.raises(ValueError, match="too long"):
            Brand.create(name=long_name, slug="test", prefix="T")

    def test_invalid_prefix_empty(self):
        """Test invalid empty prefix."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Brand.create(name="Test", slug="test", prefix="")

    def test_invalid_prefix_too_short(self):
        """Test invalid prefix too short."""
        with pytest.raises(ValueError, match="between 2 and 10"):
            Brand.create(name="Test", slug="test", prefix="A")

    def test_invalid_prefix_too_long(self):
        """Test invalid prefix too long."""
        with pytest.raises(ValueError, match="between 2 and 10"):
            Brand.create(name="Test", slug="test", prefix="A" * 11)

    def test_invalid_prefix_special_chars(self):
        """Test invalid prefix with special characters."""
        with pytest.raises(ValueError, match="alphanumeric"):
            Brand.create(name="Test", slug="test", prefix="RM@")
