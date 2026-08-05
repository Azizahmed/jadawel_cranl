from django.contrib.auth import get_user_model

from jadawel.contrib.database.fields.operations import ListFieldsOperationType
from jadawel.contrib.database.operations import ListTablesDatabaseTableOperationType
from jadawel.contrib.database.rows.operations import ReadDatabaseRowOperationType
from jadawel.contrib.database.table.operations import ListRowsDatabaseTableOperationType
from jadawel.contrib.database.views.operations import (
    ListAggregationsViewOperationType,
    ListViewDecorationOperationType,
    ListViewsOperationType,
    ReadAggregationsViewOperationType,
    ReadViewFieldOptionsOperationType,
    ReadViewOperationType,
)
from jadawel.core.permission_manager import (
    AllowIfTemplatePermissionManagerType as CoreAllowIfTemplatePermissionManagerType,
)
from jadawel.core.registries import PermissionManagerType

User = get_user_model()


class AllowIfTemplatePermissionManagerType(CoreAllowIfTemplatePermissionManagerType):
    """
    Allows read operation on templates.
    """

    DATABASE_OPERATION_ALLOWED_ON_TEMPLATES = [
        ListTablesDatabaseTableOperationType.type,
        ListFieldsOperationType.type,
        ListRowsDatabaseTableOperationType.type,
        ListViewsOperationType.type,
        ReadDatabaseRowOperationType.type,
        ReadViewOperationType.type,
        ReadViewFieldOptionsOperationType.type,
        ListViewDecorationOperationType.type,
        ListAggregationsViewOperationType.type,
        ReadAggregationsViewOperationType.type,
    ]

    @property
    def OPERATION_ALLOWED_ON_TEMPLATES(self):
        return (
            self.prev_manager_type.OPERATION_ALLOWED_ON_TEMPLATES
            + self.DATABASE_OPERATION_ALLOWED_ON_TEMPLATES
        )

    def __init__(self, prev_manager_type: PermissionManagerType):
        self.prev_manager_type = prev_manager_type
