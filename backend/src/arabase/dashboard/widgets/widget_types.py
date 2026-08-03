from typing import Any

from rest_framework import serializers

from arabase.dashboard.widgets.models import ChartWidget
from arabase.integrations.local_baserow.service_types import (
    LocalBaserowGroupedAggregateRowsUserServiceType,
)
from baserow.contrib.dashboard.data_sources.handler import DashboardDataSourceHandler
from baserow.contrib.dashboard.data_sources.models import DashboardDataSource
from baserow.contrib.dashboard.types import WidgetDict
from baserow.contrib.dashboard.widgets.models import Widget
from baserow.contrib.dashboard.widgets.registries import WidgetType
from baserow.core.services.registries import service_type_registry


class ChartWidgetType(WidgetType):
    """
    The type name matches upstream Baserow's premium chart widget so that
    dashboards and templates that contain charts import into this fork.
    """

    type = "chart"
    model_class = ChartWidget
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
    serializer_field_overrides = {
        "data_source_id": serializers.PrimaryKeyRelatedField(
            queryset=DashboardDataSource.objects.all(),
            required=False,
            default=None,
            help_text="References a data source field for the widget.",
        )
    }
    request_serializer_field_names = ["chart_type", "series_config", "show_legend"]
    request_serializer_field_overrides = {}

    class SerializedDict(WidgetDict):
        data_source_id: int
        chart_type: str
        series_config: dict
        show_legend: bool

    def prepare_value_for_db(self, values: dict, instance: Widget | None = None):
        if instance is None:
            # A chart is unusable without somewhere to read numbers from, so the
            # data source is created with the widget rather than asked for.
            available_name = DashboardDataSourceHandler().find_unused_data_source_name(
                values["dashboard"], "WidgetDataSource"
            )
            data_source = DashboardDataSourceHandler().create_data_source(
                dashboard=values["dashboard"],
                name=available_name,
                service_type=service_type_registry.get(
                    LocalBaserowGroupedAggregateRowsUserServiceType.type
                ),
            )
            values["data_source"] = data_source
        return values

    def before_trashed(self, instance: Widget):
        instance.data_source.trashed = True
        instance.data_source.save()

    def before_restore(self, instance: Widget):
        instance.data_source.trashed = False
        instance.data_source.save()

    def after_delete(self, instance: Widget):
        DashboardDataSourceHandler().delete_data_source(instance.data_source)

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: dict[str, Any],
        **kwargs,
    ) -> Any:
        if prop_name == "data_source_id" and value:
            return id_mapping["dashboard_data_sources"][value]

        if prop_name == "series_config" and value:
            return self._remap_series_config(value, id_mapping)

        return super().deserialize_property(
            prop_name,
            value,
            id_mapping,
            **kwargs,
        )

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

    def serialize_property(
        self,
        instance: Widget,
        prop_name: str,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        if prop_name == "data_source_id":
            return instance.data_source_id

        return super().serialize_property(
            instance,
            prop_name,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )
