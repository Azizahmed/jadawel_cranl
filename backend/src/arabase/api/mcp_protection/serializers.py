from rest_framework import serializers

from arabase.mcp.protection.models import (
    MCPProtectedField,
    MCPProtectedFieldState,
    MCPProtectionPolicy,
)
from jadawel.api.mcp.serializers import MCPEndpointSerializer
from jadawel.core.mcp.models import MCPEndpoint


class MCPProtectedFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="field_id", read_only=True)
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    table = serializers.SerializerMethodField()
    database = serializers.SerializerMethodField()

    class Meta:
        model = MCPProtectedField
        fields = (
            "id",
            "state",
            "safe_reason_code",
            "name",
            "type",
            "table",
            "database",
        )

    def _may_display(self, instance) -> bool:
        return instance.field_id in self.context["display_field_ids"]

    def get_name(self, instance) -> str | None:
        return instance.field.name if self._may_display(instance) else None

    def get_type(self, instance) -> str | None:
        if not self._may_display(instance):
            return None
        # Metadata must remain content-blind and safe when an upstream or
        # extension field adapter is unavailable.  The policy response still
        # exposes the stable field id/state, while callers receive no guessed
        # type and no generic 500 that could reveal adapter details.
        try:
            return instance.field.get_type().type
        except Exception:
            return None

    def get_table(self, instance) -> dict | None:
        if not self._may_display(instance):
            return None
        table = instance.field.table
        return {"id": table.id, "name": table.name}

    def get_database(self, instance) -> dict | None:
        if not self._may_display(instance):
            return None
        database = instance.field.table.database
        return {"id": database.id, "name": database.name}


class MCPProtectionPolicySerializer(serializers.ModelSerializer):
    endpoint_id = serializers.IntegerField(read_only=True)
    protected_field_count = serializers.SerializerMethodField()
    fields = MCPProtectedFieldSerializer(
        source="protected_fields", many=True, read_only=True
    )

    class Meta:
        model = MCPProtectionPolicy
        fields = (
            "endpoint_id",
            "revision",
            "lifecycle_status",
            "safe_reason_code",
            "protected_field_count",
            "fields",
            "created_on",
            "updated_on",
        )

    @staticmethod
    def get_protected_field_count(instance) -> int:
        return instance.protected_fields.filter(
            state=MCPProtectedFieldState.ACTIVE
        ).count()


class MCPEndpointProtectionSummarySerializer(serializers.ModelSerializer):
    endpoint_id = serializers.IntegerField(source="id", read_only=True)
    workspace_id = serializers.IntegerField(read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    protected_field_count = serializers.IntegerField(read_only=True)
    lifecycle_status = serializers.CharField(
        source="arabase_protection_policy.lifecycle_status", read_only=True
    )
    safe_reason_code = serializers.CharField(
        source="arabase_protection_policy.safe_reason_code", read_only=True
    )

    class Meta:
        model = MCPEndpoint
        fields = (
            "endpoint_id",
            "name",
            "workspace_id",
            "workspace_name",
            "protected_field_count",
            "lifecycle_status",
            "safe_reason_code",
        )


class CreateProtectedMCPEndpointSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    workspace_id = serializers.IntegerField(min_value=1)
    protected_field_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=True
    )
    confirm_empty_policy = serializers.BooleanField(default=False)

    def validate_protected_field_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Field IDs must be unique.")
        return value


class UpdateMCPProtectionPolicySerializer(serializers.Serializer):
    protected_field_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=True
    )
    expected_revision = serializers.IntegerField(min_value=1)
    confirm_remove_field_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=True, default=list
    )

    def validate_protected_field_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Field IDs must be unique.")
        return value

    def validate_confirm_remove_field_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Field IDs must be unique.")
        return value


class ReactivateMCPProtectionPolicySerializer(serializers.Serializer):
    expected_revision = serializers.IntegerField(min_value=1)


class CreatedProtectedMCPEndpointSerializer(MCPEndpointSerializer):
    protection_policy = MCPProtectionPolicySerializer(
        source="arabase_protection_policy", read_only=True
    )

    class Meta(MCPEndpointSerializer.Meta):
        fields = (*MCPEndpointSerializer.Meta.fields, "protection_policy")
