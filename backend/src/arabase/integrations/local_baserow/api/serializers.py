from rest_framework import serializers

from arabase.integrations.local_baserow.models import (
    SORT_ON_CHOICES,
    SORT_ON_SERIES,
    LocalBaserowTableServiceAggregationGroupBy,
    LocalBaserowTableServiceAggregationSeries,
    LocalBaserowTableServiceAggregationSortBy,
)
from baserow.contrib.database.views.models import SORT_ORDER_CHOICES, SORT_ORDER_DESC


class LocalBaserowTableServiceAggregationSeriesSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(read_only=True)
    trashed = serializers.BooleanField(
        source="field.trashed",
        read_only=True,
        help_text="A series is considered trashed if the field it's associated "
        "with is trashed.",
    )
    field_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="The id of the field being aggregated.",
    )

    class Meta:
        model = LocalBaserowTableServiceAggregationSeries
        fields = ("id", "order", "field_id", "aggregation_type", "trashed")


class LocalBaserowTableServiceAggregationGroupBySerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(read_only=True)
    trashed = serializers.BooleanField(
        source="field.trashed",
        read_only=True,
        help_text="A group by is considered trashed if the field it's associated "
        "with is trashed.",
    )
    field_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="The id of the field the aggregation is grouped by.",
    )

    class Meta:
        model = LocalBaserowTableServiceAggregationGroupBy
        fields = ("id", "order", "field_id", "trashed")


class LocalBaserowTableServiceAggregationSortBySerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(read_only=True)
    sort_on = serializers.ChoiceField(
        choices=SORT_ON_CHOICES,
        default=SORT_ON_SERIES,
        help_text="Whether the sort applies to a series value or to the group by "
        "field.",
    )
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="The series key being sorted on, when `sort_on` is `SERIES`.",
    )
    direction = serializers.ChoiceField(
        choices=SORT_ORDER_CHOICES,
        default=SORT_ORDER_DESC,
        help_text="The sort direction.",
    )

    class Meta:
        model = LocalBaserowTableServiceAggregationSortBy
        fields = ("id", "order", "sort_on", "reference", "direction")
