from dataclasses import dataclass
from typing import NewType

from jadawel.contrib.automation.models import AutomationWorkflow

AutomationWorkflowForUpdate = NewType("AutomationWorkflowForUpdate", AutomationWorkflow)


@dataclass
class UpdatedAutomationWorkflow:
    workflow: AutomationWorkflow
    original_values: dict[str, any]
    new_values: dict[str, any]
