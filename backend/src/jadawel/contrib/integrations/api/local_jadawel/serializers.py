from rest_framework import serializers

from jadawel.api.applications.serializers import ApplicationSerializer
from jadawel.contrib.database.table.models import Table
from jadawel.contrib.database.views.models import View


class LocalJadawelViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = View
        fields = ("id", "table_id", "name")


class LocalJadawelTableSerializer(serializers.ModelSerializer):
    is_data_sync = serializers.BooleanField(
        source="is_data_synced_table",
        help_text="Whether this table is a data synced table or not.",
    )
    is_two_way_data_sync = serializers.BooleanField(
        source="is_two_way_data_synced_table",
        help_text="Whether this table is a two-way data synced table or not.",
    )

    class Meta:
        model = Table
        fields = ("id", "database_id", "name", "is_data_sync", "is_two_way_data_sync")


class LocalJadawelDatabaseSerializer(ApplicationSerializer):
    tables = LocalJadawelTableSerializer(
        many=True,
        help_text="This field is specific to the `database` application and contains "
        "an array of tables that are in the database.",
    )
    views = LocalJadawelViewSerializer(
        many=True,
        help_text="This field is specific to the `database` application and contains "
        "an array of views that are in the tables.",
    )

    class Meta(ApplicationSerializer.Meta):
        ref_name = "LocalJadawelDatabaseApplication"
        fields = ApplicationSerializer.Meta.fields + ("tables", "views")


class LocalJadawelContextDataSerializer(serializers.Serializer):
    databases = LocalJadawelDatabaseSerializer(many=True)
