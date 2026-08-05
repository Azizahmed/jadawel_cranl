from jadawel.contrib.automation.nodes.operations import (
    DeleteAutomationNodeOperationType,
    UpdateAutomationNodeOperationType,
)
from jadawel.core.registries import PermissionManagerType
from jadawel.core.subjects import UserSubjectType


class AutomationNodePermissionManager(PermissionManagerType):
    """Handles permissions for Automation Nodes."""

    type = "automation_node"
    supported_actor_types = [UserSubjectType.type]

    def check_multiple_permissions(
        self,
        checks,
        workspace=None,
        include_trash=False,
    ):
        """
        If a node's workflow is published, any modifications related to it
        should be disallowed.
        """

        result = {}

        for check in checks:
            if check.operation_name in [
                DeleteAutomationNodeOperationType.type,
                UpdateAutomationNodeOperationType.type,
            ]:
                if check.context.workflow.is_published:
                    result[check] = False

        return result
