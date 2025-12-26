import datetime
import uuid

import pytest
from django.utils import timezone

from activations.domain.activation import Activation
from activations.infrastructure.models import Activation as ActivationModel
from activations.infrastructure.repositories.django_activation_repository import (
    DjangoActivationRepository,
)
from core.domain.value_objects import InstanceIdentifier, InstanceType
from licenses.infrastructure.models import License


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_repository_update_is_active(db_license):
    repo = DjangoActivationRepository()
    license_obj = await License.objects.aget(id=db_license.id)

    # 1. Create Domain Entity
    act_id = uuid.uuid4()
    activation = Activation(
        id=act_id,
        license_id=license_obj.id,
        instance_identifier=InstanceIdentifier("test-inst", InstanceType.URL),
        instance_metadata={},
        activated_at=timezone.now(),
        last_checked_at=timezone.now(),
        deactivated_at=None,
        is_active=True,
    )

    # 2. Save (Create)
    saved = await repo.save(activation)
    assert saved.is_active is True

    # 3. Verify in DB
    model = await ActivationModel.objects.aget(id=act_id)
    assert model.is_active is True

    # 4. Deactivate in Domain
    deactivated = activation.deactivate()
    assert deactivated.is_active is False

    # 5. Save (Update)
    updated = await repo.save(deactivated)
    assert updated.is_active is False

    # 6. Verify in DB
    model = await ActivationModel.objects.aget(id=act_id)
    if model.is_active:
        print(f"FAILURE: Model is_active is {model.is_active} (Expected False)")
        print(f"Model ID: {model.id}")
        print(f"Model keys: {model._meta.fields}")
    assert model.is_active is False
