from jadawel.contrib.dashboard.data_sources.operations import (
    DispatchDashboardDataSourceOperationType,
    ListDashboardDataSourcesOperationType,
    ReadDashboardDataSourceOperationType,
)
from jadawel.contrib.dashboard.widgets.operations import (
    ListWidgetsOperationType,
    ReadWidgetOperationType,
)
from jadawel.core.permission_manager import (
    AllowIfTemplatePermissionManagerType as CoreAllowIfTemplatePermissionManagerType,
)
from jadawel.core.registries import PermissionManagerType


class AllowIfTemplatePermissionManagerType(CoreAllowIfTemplatePermissionManagerType):
    """
    Allows read operation on templates.
    """

    DASHBOARD_OPERATION_ALLOWED_ON_TEMPLATES = [
        ReadWidgetOperationType.type,
        ListWidgetsOperationType.type,
        ReadDashboardDataSourceOperationType.type,
        ListDashboardDataSourcesOperationType.type,
        DispatchDashboardDataSourceOperationType.type,
    ]

    @property
    def OPERATION_ALLOWED_ON_TEMPLATES(self):
        return (
            self.prev_manager_type.OPERATION_ALLOWED_ON_TEMPLATES
            + self.DASHBOARD_OPERATION_ALLOWED_ON_TEMPLATES
        )

    def __init__(self, prev_manager_type: PermissionManagerType):
        self.prev_manager_type = prev_manager_type
