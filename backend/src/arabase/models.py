"""Model registry entry point for the ``arabase`` app.

Django only discovers models that are importable from ``<app>.models``, so every
model the fork adds is re-exported here even though it is defined next to the
code that uses it.
"""

from arabase.dashboard.widgets.models import (
    ChartWidget,
    ProgressWidget,
    RecordsListWidget,
    UpcomingDatesWidget,
)
from arabase.integrations.local_baserow.models import (
    LocalBaserowGroupedAggregateRows,
    LocalBaserowTableServiceAggregationGroupBy,
    LocalBaserowTableServiceAggregationSeries,
    LocalBaserowTableServiceAggregationSortBy,
    LocalBaserowUpcomingRows,
)

__all__ = [
    "ChartWidget",
    "ProgressWidget",
    "RecordsListWidget",
    "UpcomingDatesWidget",
    "LocalBaserowGroupedAggregateRows",
    "LocalBaserowTableServiceAggregationGroupBy",
    "LocalBaserowTableServiceAggregationSeries",
    "LocalBaserowTableServiceAggregationSortBy",
    "LocalBaserowUpcomingRows",
]
