from django.contrib.auth import get_user_model

from jadawel.contrib.builder.data_sources.operations import (
    DispatchDataSourceOperationType,
    ListDataSourcesPageOperationType,
)
from jadawel.contrib.builder.elements.operations import ListElementsPageOperationType
from jadawel.contrib.builder.operations import ListPagesBuilderOperationType
from jadawel.contrib.builder.workflow_actions.operations import (
    ListBuilderWorkflowActionsPageOperationType,
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

    BUILDER_OPERATION_ALLOWED_ON_TEMPLATES = [
        ListPagesBuilderOperationType.type,
        ListElementsPageOperationType.type,
        ListBuilderWorkflowActionsPageOperationType.type,
        DispatchDataSourceOperationType.type,
        ListDataSourcesPageOperationType.type,
    ]

    @property
    def OPERATION_ALLOWED_ON_TEMPLATES(self):
        return (
            self.prev_manager_type.OPERATION_ALLOWED_ON_TEMPLATES
            + self.BUILDER_OPERATION_ALLOWED_ON_TEMPLATES
        )

    def __init__(self, prev_manager_type: PermissionManagerType):
        self.prev_manager_type = prev_manager_type
