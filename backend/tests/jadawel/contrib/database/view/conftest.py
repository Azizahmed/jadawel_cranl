import pytest

from jadawel.contrib.database.views.registries import (
    view_ownership_type_registry,
)


def pytest_collection_modifyitems(items):
    if "personal" in view_ownership_type_registry.get_types():
        return

    skip_personal_ownership = pytest.mark.skip(
        reason="The OSS-only Jadawel build has no personal view ownership type."
    )
    for item in items:
        if item.get_closest_marker("view_ownership") is not None:
            item.add_marker(skip_personal_ownership)
