from django.contrib.auth.models import AbstractUser
from django.db.models import QuerySet

from jadawel.contrib.automation.history.handler import AutomationHistoryHandler
from jadawel.contrib.automation.history.models import AutomationWorkflowHistory
from jadawel.contrib.automation.workflows.handler import AutomationWorkflowHandler
from jadawel.contrib.automation.workflows.operations import (
    ReadAutomationWorkflowOperationType,
)
from jadawel.core.handler import CoreHandler


class AutomationHistoryService:
    def __init__(self):
        self.handler = AutomationHistoryHandler()
        self.workflow_handler = AutomationWorkflowHandler()

    def get_workflow_histories(
        self, user: AbstractUser, workflow_id: int
    ) -> QuerySet[AutomationWorkflowHistory]:
        """
        Returns an AutomationWorkflowHistory queryset related to a workflow.

        :param user: The user requesting the workflow history.
        :param workflow_id: The ID of the workflow.
        :return: A queryset of workflow histories.
        """

        workflow = self.workflow_handler.get_workflow(workflow_id)

        CoreHandler().check_permissions(
            user,
            ReadAutomationWorkflowOperationType.type,
            workspace=workflow.automation.workspace,
            context=workflow,
        )

        return self.handler.get_workflow_histories(workflow)
