from typing import Any

from rest_framework import serializers

from arabase.dashboard.widgets.base import (
    DataSourceBackedWidgetType,
    DisplayedFieldsWidgetTypeMixin,
)
from arabase.dashboard.widgets.models import (
    ChartWidget,
    ProgressWidget,
    RecordsListWidget,
    UpcomingDatesWidget,
)
from arabase.integrations.local_jadawel.service_types import (
    LocalJadawelGroupedAggregateRowsUserServiceType,
)
from arabase.integrations.local_jadawel.upcoming_rows import (
    LocalJadawelUpcomingRowsUserServiceType,
)
from jadawel.contrib.dashboard.widgets.registries import WidgetType
from jadawel.contrib.integrations.local_jadawel.service_types import (
    LocalJadawelAggregateRowsUserServiceType,
    LocalJadawelListRowsUserServiceType,
)

MAX_DISPLAYED_FIELDS = 6
"""More columns than this stop being readable inside a dashboard widget, whatever
the widget's width."""


class ChartWidgetType(DataSourceBackedWidgetType):
    """
    The type name matches upstream Baserow's premium chart widget so that
    dashboards and templates that contain charts import into this fork.
    """

    type = "chart"
    model_class = ChartWidget
    service_type_name = LocalJadawelGroupedAggregateRowsUserServiceType.type
    allowed_fields = WidgetType.allowed_fields + [
        "chart_type",
        "series_config",
        "show_legend",
    ]
    serializer_field_names = [
        "data_source_id",
        "chart_type",
        "series_config",
        "show_legend",
    ]
    request_serializer_field_names = ["chart_type", "series_config", "show_legend"]
    request_serializer_field_overrides = {}

    class SerializedDict(DataSourceBackedWidgetType.SerializedDict):
        chart_type: str
        series_config: dict
        show_legend: bool

    @property
    def serializer_field_overrides(self):
        return self.data_source_serializer_field_overrides

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: dict[str, Any],
        **kwargs,
    ) -> Any:
        if prop_name == "series_config" and value:
            return self._remap_series_config(value, id_mapping)

        return super().deserialize_property(prop_name, value, id_mapping, **kwargs)

    @staticmethod
    def _remap_series_config(series_config: dict, id_mapping: dict[str, Any]) -> dict:
        """
        `series_config` is keyed by `field_<id>_<aggregation type>`, so the field
        ids inside those keys have to be remapped or every override would be
        orphaned after an import.
        """

        field_mapping = id_mapping.get("database_fields", {})
        remapped = {}
        for key, config in series_config.items():
            parts = key.split("_", 2)
            if len(parts) == 3 and parts[0] == "field" and parts[1].isdigit():
                new_field_id = field_mapping.get(int(parts[1]), None)
                if new_field_id is not None:
                    key = f"field_{new_field_id}_{parts[2]}"
            remapped[key] = config
        return remapped


class RecordsListWidgetType(DisplayedFieldsWidgetTypeMixin, DataSourceBackedWidgetType):
    """The latest rows of a table or view."""

    type = "records_list"
    model_class = RecordsListWidget
    service_type_name = LocalJadawelListRowsUserServiceType.type
    allowed_fields = WidgetType.allowed_fields + ["field_ids"]
    serializer_field_names = ["data_source_id", "field_ids"]
    request_serializer_field_names = ["field_ids"]
    request_serializer_field_overrides = {}

    class SerializedDict(DataSourceBackedWidgetType.SerializedDict):
        field_ids: list

    @property
    def serializer_field_overrides(self):
        return {
            **self.data_source_serializer_field_overrides,
            "field_ids": serializers.ListField(
                child=serializers.IntegerField(),
                required=False,
                max_length=MAX_DISPLAYED_FIELDS,
                help_text="Ids of the fields to show, in order. An empty list "
                "lets the widget choose.",
            ),
        }


class ProgressWidgetType(DataSourceBackedWidgetType):
    """An aggregation measured against a target."""

    type = "progress"
    model_class = ProgressWidget
    service_type_name = LocalJadawelAggregateRowsUserServiceType.type
    allowed_fields = WidgetType.allowed_fields + [
        "target_value",
        "display_style",
        "warning_threshold",
        "success_threshold",
    ]
    serializer_field_names = [
        "data_source_id",
        "target_value",
        "display_style",
        "warning_threshold",
        "success_threshold",
    ]
    request_serializer_field_names = [
        "target_value",
        "display_style",
        "warning_threshold",
        "success_threshold",
    ]
    request_serializer_field_overrides = {}

    class SerializedDict(DataSourceBackedWidgetType.SerializedDict):
        target_value: str
        display_style: str
        warning_threshold: int
        success_threshold: int

    @property
    def serializer_field_overrides(self):
        return self.data_source_serializer_field_overrides

    def prepare_value_for_db(self, values: dict, instance=None):
        values = super().prepare_value_for_db(values, instance)

        # A target of zero would make every percentage a division by zero, and a
        # negative one has no meaning as a goal.
        target = values.get("target_value", None)
        if target is not None and target <= 0:
            raise serializers.ValidationError(
                {"target_value": "The target value must be greater than zero."}
            )

        # Thresholds that cross over would colour the widget by whichever check
        # happened to run first.
        warning = values.get(
            "warning_threshold", getattr(instance, "warning_threshold", None)
        )
        success = values.get(
            "success_threshold", getattr(instance, "success_threshold", None)
        )
        if warning is not None and success is not None and warning > success:
            raise serializers.ValidationError(
                {
                    "warning_threshold": "The warning threshold cannot be above "
                    "the success threshold."
                }
            )

        return values


class UpcomingDatesWidgetType(
    DisplayedFieldsWidgetTypeMixin, DataSourceBackedWidgetType
):
    """An agenda of rows falling due soon."""

    type = "upcoming_dates"
    model_class = UpcomingDatesWidget
    service_type_name = LocalJadawelUpcomingRowsUserServiceType.type
    allowed_fields = WidgetType.allowed_fields + ["field_ids"]
    serializer_field_names = ["data_source_id", "field_ids"]
    request_serializer_field_names = ["field_ids"]
    request_serializer_field_overrides = {}

    class SerializedDict(DataSourceBackedWidgetType.SerializedDict):
        field_ids: list

    @property
    def serializer_field_overrides(self):
        return {
            **self.data_source_serializer_field_overrides,
            "field_ids": serializers.ListField(
                child=serializers.IntegerField(),
                required=False,
                max_length=MAX_DISPLAYED_FIELDS,
                help_text="Ids of the fields to show alongside the date, in order.",
            ),
        }
