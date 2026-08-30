from django.db.models import Count

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from arabase.api.mcp_protection.serializers import (
    MCPEndpointProtectionSummarySerializer,
    MCPProtectionPolicySerializer,
)
from arabase.mcp.protection.models import MCPProtectionPolicy
from jadawel.api.decorators import map_exceptions
from jadawel.api.mcp.errors import ERROR_MCP_ENDPOINT_DOES_NOT_EXIST
from jadawel.api.schemas import get_error_schema
from jadawel.contrib.database.fields.operations import ReadFieldOperationType
from jadawel.core.exceptions import PermissionException
from jadawel.core.handler import CoreHandler
from jadawel.core.mcp.exceptions import MCPEndpointDoesNotExist
from jadawel.core.mcp.handler import MCPEndpointHandler
from jadawel.core.mcp.models import MCPEndpoint


def _may_display_field_metadata(user, field) -> bool:
    try:
        CoreHandler().check_permissions(
            user,
            ReadFieldOperationType.type,
            workspace=field.table.database.workspace,
            context=field,
        )
    except PermissionException:
        return False
    return True


class MCPProtectionPolicyView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Arabase MCP protection"],
        operation_id="get_mcp_protection_policy",
        responses={
            200: MCPProtectionPolicySerializer,
            404: get_error_schema(["ERROR_MCP_ENDPOINT_DOES_NOT_EXIST"]),
        },
    )
    @map_exceptions({MCPEndpointDoesNotExist: ERROR_MCP_ENDPOINT_DOES_NOT_EXIST})
    def get(self, request: Request, endpoint_id: int) -> Response:
        endpoint = MCPEndpointHandler().get_endpoint(request.user, endpoint_id)
        policy = MCPProtectionPolicy.objects.prefetch_related(
            "protected_fields__field__table__database__workspace"
        ).get(endpoint=endpoint)
        display_field_ids = {
            relation.field_id
            for relation in policy.protected_fields.all()
            if _may_display_field_metadata(request.user, relation.field)
        }
        return Response(
            MCPProtectionPolicySerializer(
                policy, context={"display_field_ids": display_field_ids}
            ).data
        )


class MCPEndpointProtectionSummariesView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Arabase MCP protection"],
        operation_id="list_mcp_endpoint_protection_summaries",
        responses={200: MCPEndpointProtectionSummarySerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        endpoints = (
            MCPEndpoint.objects.filter(user=request.user)
            .select_related("workspace", "arabase_protection_policy")
            .annotate(
                protected_field_count=Count(
                    "arabase_protection_policy__protected_fields"
                )
            )
        )
        return Response(
            MCPEndpointProtectionSummarySerializer(endpoints, many=True).data
        )
