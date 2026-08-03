from django.db import models

from baserow.contrib.dashboard.widgets.models import Widget

CHART_TYPE_BAR = "bar"
CHART_TYPE_LINE = "line"
CHART_TYPE_PIE = "pie"
CHART_TYPE_DOUGHNUT = "doughnut"
CHART_TYPE_CHOICES = [
    (CHART_TYPE_BAR, "Bar"),
    (CHART_TYPE_LINE, "Line"),
    (CHART_TYPE_PIE, "Pie"),
    (CHART_TYPE_DOUGHNUT, "Doughnut"),
]


class ChartWidget(Widget):
    """
    A widget that renders a grouped aggregation as a bar, line, pie or
    doughnut chart.

    The four chart types are one widget type rather than four, because they all
    need exactly the same configuration and users routinely try one and switch
    to another. The picker still offers four tiles; they differ only in the
    `chart_type` they preset.
    """

    data_source = models.ForeignKey(
        "dashboard.DashboardDataSource",
        on_delete=models.PROTECT,
        help_text="The grouped aggregation this chart renders.",
    )
    chart_type = models.CharField(
        max_length=16,
        choices=CHART_TYPE_CHOICES,
        default=CHART_TYPE_BAR,
        db_default=CHART_TYPE_BAR,
        help_text="How the aggregation is drawn.",
    )
    series_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-series display overrides, keyed by series key "
        "(`field_<id>_<aggregation type>`). Supports `color` and `label`.",
    )
    show_legend = models.BooleanField(
        default=True,
        db_default=True,
        help_text="Whether the chart's legend is shown.",
    )
