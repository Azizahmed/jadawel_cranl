import pytest

from jadawel.core.app_auth_providers.registries import (
    app_auth_provider_type_registry,
)


@pytest.fixture(autouse=True)
def require_concrete_app_auth_provider_type():
    if not list(app_auth_provider_type_registry.get_all()):
        pytest.skip("The OSS-only Jadawel build has no concrete app-auth provider.")
