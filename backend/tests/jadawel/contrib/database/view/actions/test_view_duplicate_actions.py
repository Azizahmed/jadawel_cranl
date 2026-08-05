import pytest

from jadawel.contrib.database.action.scopes import TableActionScopeType
from jadawel.contrib.database.views.actions import DuplicateViewActionType
from jadawel.contrib.database.views.models import View
from jadawel.core.action.handler import ActionHandler
from jadawel.core.action.registries import action_type_registry


@pytest.mark.django_db
def test_can_undo_duplicate_view(data_fixture):
    session_id = "session-id"
    user = data_fixture.create_user(session_id=session_id)
    table = data_fixture.create_database_table(user)
    grid_view = data_fixture.create_grid_view(table=table)

    new_view = action_type_registry.get_by_type(DuplicateViewActionType).do(
        user, grid_view
    )

    assert View.objects.count() == 2

    ActionHandler.undo(user, [TableActionScopeType.value(table.id)], session_id)

    assert View.objects.count() == 1


@pytest.mark.django_db
def test_can_undo_redo_create_view(data_fixture):
    session_id = "session-id"
    user = data_fixture.create_user(session_id=session_id)
    table = data_fixture.create_database_table(user)
    grid_view = data_fixture.create_grid_view(table=table)

    action_type_registry.get_by_type(DuplicateViewActionType).do(user, grid_view)

    assert View.objects.count() == 2

    ActionHandler.undo(user, [TableActionScopeType.value(table.id)], session_id)

    assert View.objects.count() == 1

    ActionHandler.redo(user, [TableActionScopeType.value(table.id)], session_id)

    assert View.objects.count() == 2
