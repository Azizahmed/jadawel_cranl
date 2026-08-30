"""Authenticated API for reviewing MCP-authored protected page artifacts."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from arabase.mcp.protection.artifact_boundary import (
    approve_artifact_draft,
    artifact_status_for_view,
    revoke_artifact,
    submit_mcp_page_change,
)
from arabase.mcp.protection.models import ArtifactAudience
from arabase.views.models import HtmlPageView
from jadawel.contrib.database.views.exceptions import ViewDoesNotExist
from jadawel.contrib.database.views.handler import ViewHandler
from jadawel.core.mcp.handler import MCPEndpointHandler


def _get_endpoint_and_view(request, endpoint_id: int, view_id: int):
    endpoint = MCPEndpointHandler().get_endpoint(request.user, endpoint_id)
    try:
        view = ViewHandler().get_view_as_user(request.user, view_id, HtmlPageView)
    except Exception as exc:
        raise ViewDoesNotExist() from exc
    if view.table.database.workspace_id != endpoint.workspace_id:
        raise ViewDoesNotExist()
    return endpoint, view


class ArtifactDraftView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        endpoint, view = _get_endpoint_and_view(
            request, request.data.get("endpoint_id"), request.data.get("view_id")
        )
        result = submit_mcp_page_change(
            user=request.user,
            endpoint=endpoint,
            view=view,
            html=request.data.get("html", ""),
            protected_field_ids=request.data.get("protected_field_ids", []),
            audience=request.data.get("audience", ArtifactAudience.AUTHENTICATED),
            pending_view_values=request.data.get("pending_view_values", {}),
        )
        return Response(result, status=201 if result.get("draft_id") else 200)


class ArtifactDraftApprovalView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, draft_id: int):
        return Response(approve_artifact_draft(user=request.user, draft_id=draft_id))


class ArtifactRevokeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, view_id: int):
        return Response(
            revoke_artifact(
                user=request.user,
                view_id=view_id,
                reason=request.data.get("reason", "manual_revocation"),
            )
        )


class ArtifactStateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, view_id: int):
        view = ViewHandler().get_view_as_user(request.user, view_id, HtmlPageView)
        return Response(artifact_status_for_view(view))
