from jadawel.contrib.automation.models import Automation
from jadawel.core.search.search_types import ApplicationSearchType


class AutomationSearchType(ApplicationSearchType):
    """
    Searchable item type specifically for automations.
    """

    type = "automation"
    name = "Automation"
    model_class = Automation
    priority = 4
