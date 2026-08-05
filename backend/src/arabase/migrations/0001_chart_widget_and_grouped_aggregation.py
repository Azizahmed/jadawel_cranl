import django.db.models.deletion
from django.db import migrations, models

import jadawel.core.formula.field


class Migration(migrations.Migration):
    """
    The fork's first migration: the grouped aggregation service behind dashboard
    charts, and the chart widget itself.

    Both live in `arabase` rather than in `integrations` / `dashboard` so that the
    fork never inserts a migration into an upstream app's sequence, which would
    conflict on every merge from upstream.
    """

    initial = True

    dependencies = [
        ("core", "0116_jadawel_arabic_english_only"),
        ("dashboard", "0003_widget_dashboarddatasource_summarywidget"),
        ("database", "0210_jadawel_rename_default_grid_views"),
    ]

    operations = [
        migrations.CreateModel(
            name="LocalBaserowGroupedAggregateRows",
            fields=[
                (
                    "service_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.service",
                    ),
                ),
                (
                    "search_query",
                    jadawel.core.formula.field.FormulaField(
                        help_text="The query to apply to the service to narrow "
                        "the results down."
                    ),
                ),
                (
                    "filter_type",
                    models.CharField(
                        choices=[("AND", "And"), ("OR", "Or")],
                        default="AND",
                        help_text="Indicates whether all the rows should apply to "
                        "all filters (AND) or to any filter (OR).",
                        max_length=3,
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="database.table",
                    ),
                ),
                (
                    "view",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="database.view",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("core.service", models.Model),
        ),
        migrations.CreateModel(
            name="LocalBaserowTableServiceAggregationSeries",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "aggregation_type",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="The field aggregation type.",
                        max_length=48,
                    ),
                ),
                ("order", models.PositiveIntegerField()),
                (
                    "field",
                    models.ForeignKey(
                        help_text="The aggregated field.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="database.field",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        help_text="The service this aggregation series belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_aggregation_series",
                        to="arabase.localbaserowgroupedaggregaterows",
                    ),
                ),
            ],
            options={
                "ordering": ("order", "id"),
            },
        ),
        migrations.CreateModel(
            name="LocalBaserowTableServiceAggregationGroupBy",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveIntegerField()),
                (
                    "field",
                    models.ForeignKey(
                        help_text="The field to group the aggregation by.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="database.field",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        help_text="The service this group by belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_aggregation_group_bys",
                        to="arabase.localbaserowgroupedaggregaterows",
                    ),
                ),
            ],
            options={
                "ordering": ("order", "id"),
            },
        ),
        migrations.CreateModel(
            name="LocalBaserowTableServiceAggregationSortBy",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sort_on",
                    models.CharField(
                        choices=[("SERIES", "SERIES"), ("GROUP_BY", "GROUP_BY")],
                        default="SERIES",
                        help_text="Whether the sort applies to a series value or "
                        "the group by field.",
                        max_length=10,
                    ),
                ),
                (
                    "reference",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="The series key or group by field reference being "
                        "sorted on.",
                        max_length=255,
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        choices=[("ASC", "Ascending"), ("DESC", "Descending")],
                        default="DESC",
                        help_text="Indicates the sort order direction.",
                        max_length=4,
                    ),
                ),
                ("order", models.PositiveIntegerField()),
                (
                    "service",
                    models.ForeignKey(
                        help_text="The service this sort belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_aggregation_sorts",
                        to="arabase.localbaserowgroupedaggregaterows",
                    ),
                ),
            ],
            options={
                "ordering": ("order", "id"),
            },
        ),
        migrations.CreateModel(
            name="ChartWidget",
            fields=[
                (
                    "widget_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="dashboard.widget",
                    ),
                ),
                (
                    "chart_type",
                    models.CharField(
                        choices=[
                            ("bar", "Bar"),
                            ("line", "Line"),
                            ("pie", "Pie"),
                            ("doughnut", "Doughnut"),
                        ],
                        db_default="bar",
                        default="bar",
                        help_text="How the aggregation is drawn.",
                        max_length=16,
                    ),
                ),
                (
                    "series_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Per-series display overrides, keyed by series key "
                        "(`field_<id>_<aggregation type>`). Supports `color` and "
                        "`label`.",
                    ),
                ),
                (
                    "show_legend",
                    models.BooleanField(
                        db_default=True,
                        default=True,
                        help_text="Whether the chart's legend is shown.",
                    ),
                ),
                (
                    "data_source",
                    models.ForeignKey(
                        help_text="The grouped aggregation this chart renders.",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="dashboard.dashboarddatasource",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("dashboard.widget",),
        ),
    ]
