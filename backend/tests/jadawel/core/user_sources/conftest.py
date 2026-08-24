import pytest

from jadawel.core.user_sources.registries import user_source_type_registry


@pytest.fixture(autouse=True)
def require_concrete_user_source_type():
    if not list(user_source_type_registry.get_all()):
        pytest.skip("The OSS-only Jadawel build has no concrete user-source provider.")
