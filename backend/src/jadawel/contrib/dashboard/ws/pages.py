from jadawel.contrib.dashboard.exceptions import DashboardDoesNotExist
from jadawel.contrib.dashboard.handler import DashboardHandler
from jadawel.contrib.dashboard.widgets.operations import ListWidgetsOperationType
from jadawel.core.exceptions import PermissionException
from jadawel.core.handler import CoreHandler
from jadawel.ws.registries import PageType


class DashboardPageType(PageType):
    type = "dashboard"
    parameters = ["dashboard_id"]

    def can_add(self, user, web_socket_id, dashboard_id, **kwargs):
        """
        The user should only have access to this page if the dashboard
        exists and if they have access to it.
        """

        if not dashboard_id:
            return False

        try:
            dashboard = DashboardHandler().get_dashboard(dashboard_id)
            CoreHandler().check_permissions(
                user,
                ListWidgetsOperationType.type,
                workspace=dashboard.workspace,
                context=dashboard,
            )
        except (DashboardDoesNotExist, PermissionException):
            return False

        return True

    def get_group_name(self, dashboard_id, **kwargs):
        return f"dashboard-{dashboard_id}"

    def get_permission_channel_group_name(self, dashboard_id, **kwargs):
        return f"permissions-dashboard-{dashboard_id}"
