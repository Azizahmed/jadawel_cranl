"""Model registry entry point for the ``arabase`` app.

Django only discovers models that are importable from ``<app>.models``, so every
model the fork adds is re-exported here even though it is defined next to the
code that uses it.
"""

from arabase.backup.models import BackupRun, BackupSchedule
from arabase.dashboard.share.models import DashboardShare
from arabase.dashboard.widgets.models import (
    ChartWidget,
    ProgressWidget,
    RecordsListWidget,
    UpcomingDatesWidget,
)
from arabase.integrations.local_jadawel.models import (
    LocalJadawelGroupedAggregateRows,
    LocalJadawelTableServiceAggregationGroupBy,
    LocalJadawelTableServiceAggregationSeries,
    LocalJadawelTableServiceAggregationSortBy,
    LocalJadawelUpcomingRows,
)
from arabase.views.models import (
    HtmlPageView,
    HtmlPageViewFieldOptions,
    HtmlPageViewRevision,
)

__all__ = [
    "BackupRun",
    "BackupSchedule",
    "DashboardShare",
    "ChartWidget",
    "ProgressWidget",
    "RecordsListWidget",
    "UpcomingDatesWidget",
    "LocalJadawelGroupedAggregateRows",
    "LocalJadawelTableServiceAggregationGroupBy",
    "LocalJadawelTableServiceAggregationSeries",
    "LocalJadawelTableServiceAggregationSortBy",
    "LocalJadawelUpcomingRows",
    "HtmlPageView",
    "HtmlPageViewFieldOptions",
    "HtmlPageViewRevision",
]
