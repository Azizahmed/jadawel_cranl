from typing import TypedDict, TypeVar

from jadawel.core.workflow_actions.models import WorkflowAction


class WorkflowActionDict(TypedDict):
    id: int
    type: str
    order: int


WorkflowActionDictSubClass = TypeVar(
    "WorkflowActionDictSubClass", bound=WorkflowActionDict
)
WorkflowActionSubClass = TypeVar("WorkflowActionSubClass", bound=WorkflowAction)
