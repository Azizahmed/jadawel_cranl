from collections import defaultdict

from django.db import transaction

from jadawel.config.celery import app
from jadawel.contrib.database.table.object_scopes import DatabaseTableObjectScopeType
from jadawel.contrib.database.table.operations import (
    ListenToAllDatabaseTableEventsOperationType,
)
from jadawel.contrib.database.table.signals import table_usage_updated
from jadawel.contrib.database.ws.pages import TablePageType
from jadawel.core.exceptions import PermissionException
from jadawel.core.mixins import TrashableModelMixin
from jadawel.core.models import Workspace
from jadawel.core.object_scopes import WorkspaceObjectScopeType
from jadawel.core.registries import (
    PermissionManagerType,
    object_scope_type_registry,
    subject_type_registry,
)
from jadawel.core.subjects import UserSubjectType
from jadawel.ws.tasks import send_message_to_channel_group


def unsubscribe_subject_from_tables_currently_subscribed_to(
    subject_id: int,
    subject_type_name: str,
    scope_id: int,
    scope_type_name: str,
    workspace_id: int,
    permission_manager: PermissionManagerType = None,
):
    """
    Unsubscribes all users associated to a subject from the tables they are currently
    subscribed to. Optionally you can also recheck their permissions before deciding
    to unsubscribe them.

    :param subject_id: The id for the subject we are trying to unsubscribe
    :param subject_type_name: The name of the subject type
    :param scope_id: The id of the scope the subject should be removed from
    :param scope_type_name: The name of the scope type
    :param workspace_id: The id of the workspace in which context this is executed
    :param permission_manager: Optional parameter used to check permissions
    """

    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    workspace = Workspace.objects.get(pk=workspace_id)

    subject_type = subject_type_registry.get(subject_type_name)
    scope_type = object_scope_type_registry.get(scope_type_name)

    if issubclass(subject_type.model_class, TrashableModelMixin):
        subject_type_qs = subject_type.model_class.objects_and_trash
    else:
        subject_type_qs = subject_type.model_class.objects

    subject = subject_type_qs.get(pk=subject_id)
    scope = scope_type.model_class.objects.get(pk=scope_id)

    users = subject_type.get_users_included_in_subject(subject)
    tables = DatabaseTableObjectScopeType().get_all_context_objects_in_scope(scope)

    channel_group_names_users_dict = defaultdict(set)
    for user in users:
        for table in tables:
            channel_group_name = TablePageType().get_permission_channel_group_name(
                table.id
            )
            if permission_manager is None:
                channel_group_names_users_dict[channel_group_name].add(user.id)
            else:
                try:
                    permission_manager.check_permissions(
                        user,
                        ListenToAllDatabaseTableEventsOperationType.type,
                        workspace=workspace,
                        context=table,
                    )
                except PermissionException:
                    channel_group_names_users_dict[channel_group_name].add(user.id)

    channel_layer = get_channel_layer()

    for channel_group_name, user_ids in channel_group_names_users_dict.items():
        async_to_sync(send_message_to_channel_group)(
            channel_layer,
            channel_group_name,
            {
                "type": "users_removed_from_permission_group",
                "user_ids_to_remove": list(user_ids),
                "permission_group_name": channel_group_name,
            },
        )


@app.task(
    name="jadawel.contrib.database.table.tasks.unsubscribe_user_from_tables_when_removed_from_workspace",
    bind=True,
)
def unsubscribe_user_from_tables_when_removed_from_workspace(
    self,
    user_id: int,
    workspace_id: int,
):
    """
    Task that will unsubscribe the provided user from web socket
    CoreConsumer pages that belong to the provided workspace.

    :param user_id: The id of the user that is supposed to be unsubscribed.
    :param workspace_id: The id of the workspace the user belonged to.
    """

    unsubscribe_subject_from_tables_currently_subscribed_to(
        user_id,
        UserSubjectType.type,
        workspace_id,
        WorkspaceObjectScopeType.type,
        workspace_id,
    )


@app.task(
    name="jadawel.contrib.database.table.tasks.setup_created_by_and_last_modified_by_column",
    bind=True,
    queue="export",
)
def setup_created_by_and_last_modified_by_column(self, table_id: int):
    from jadawel.contrib.database.table.handler import TableHandler

    with transaction.atomic():
        table = TableHandler().get_table_for_update(table_id)
        TableHandler().create_created_by_and_last_modified_by_fields(table)


@app.task(
    name="jadawel.contrib.database.table.tasks.setup_m2m_field_indexes_if_not_exist",
    bind=True,
    queue="export",
)
def setup_m2m_field_indexes_if_not_exist(self, table_id: int):
    from jadawel.contrib.database.db.schema import safe_django_schema_editor
    from jadawel.contrib.database.table.handler import TableHandler

    with transaction.atomic():
        table = TableHandler().get_table_for_update(table_id)
        model = table.get_model()
        fields = model.get_fields()

        with safe_django_schema_editor(atomic=False) as schema_editor:
            for field in fields:
                model_field = model._meta.get_field(field.db_column)
                schema_editor.ensure_m2m_field_indexes(model_field)

        table.missing_m2m_indexes_added = True
        table.save(update_fields=["missing_m2m_indexes_added"])


@app.task(name="jadawel.contrib.database.table.tasks.update_table_usage", bind=True)
def update_table_usage(self, table_id: int, row_count: int = 0):
    from jadawel.contrib.database.table.handler import TableUsageHandler

    TableUsageHandler.mark_table_for_usage_update(table_id, row_count)

    table_usage_updated.send(sender=self, table_id=table_id)


@app.task(
    name="jadawel.contrib.database.table.tasks.create_tables_usage_for_new_database",
    bind=True,
)
def create_tables_usage_for_new_database(self, database_id: int):
    from jadawel.contrib.database.table.handler import TableUsageHandler

    TableUsageHandler.create_tables_usage_for_new_database(database_id)
