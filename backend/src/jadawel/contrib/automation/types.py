from typing import List, TypedDict

from jadawel.contrib.automation.nodes.types import AutomationNodeDict
from jadawel.contrib.automation.workflows.constants import WorkflowState
from jadawel.core.integrations.types import IntegrationDictSubClass


class AutomationWorkflowDict(TypedDict):
    id: int
    name: str
    order: int
    nodes: List[AutomationNodeDict]
    state: WorkflowState
    graph: dict
    notification_recipient_emails: List[str]


class AutomationDict(TypedDict):
    id: int
    name: str
    order: int
    type: str
    workflows: List[AutomationWorkflowDict]
    integrations: List[IntegrationDictSubClass]
