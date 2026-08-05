from jadawel.contrib.dashboard.models import Dashboard
from jadawel.core.search.search_types import ApplicationSearchType


class DashboardSearchType(ApplicationSearchType):
    """
    Searchable item type specifically for dashboards.
    """

    type = "dashboard"
    name = "Dashboard"
    model_class = Dashboard
    priority = 3
