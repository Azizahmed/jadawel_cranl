"""Authenticated API for reviewing MCP-authored protected page artifacts."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from arabase.api.html_page.errors import ERROR_HTML_PAGE_DOES_NOT_EXIST
from arabase.api.mcp_protection.serializers import (
    ArtifactDraftRequestSerializer,
    ArtifactRevokeSerializer,
)
from arabase.mcp.protection.artifact_boundary import (
    approve_artifact_draft,
    artifact_status_for_view,
    revoke_artifact,
    submit_mcp_page_change,
)
from arabase.mcp.protection.models import (
    ArtifactDraft,
    HtmlPageArtifactState,
)
from arabase.views.models import HtmlPageView
from jadawel.api.decorators import map_exceptions, validate_body
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

    @map_exceptions({ViewDoesNotExist: ERROR_HTML_PAGE_DOES_NOT_EXIST})
    @validate_body(ArtifactDraftRequestSerializer, return_validated=True)
    def post(self, request, data):
        endpoint, view = _get_endpoint_and_view(
            request, data["endpoint_id"], data["view_id"]
        )
        result = submit_mcp_page_change(
            user=request.user,
            endpoint=endpoint,
            view=view,
            html=data["html"],
            protected_field_ids=data["protected_field_ids"],
            audience=data["audience"],
            pending_view_values=data["pending_view_values"],
        )
        return Response(result, status=201 if result.get("draft_id") else 200)


class ArtifactDraftApprovalView(APIView):
    permission_classes = (IsAuthenticated,)

    @map_exceptions(
        {
            ArtifactDraft.DoesNotExist: ERROR_HTML_PAGE_DOES_NOT_EXIST,
        }
    )
    def post(self, request, draft_id: int):
        return Response(approve_artifact_draft(user=request.user, draft_id=draft_id))


class ArtifactRevokeView(APIView):
    permission_classes = (IsAuthenticated,)

    @map_exceptions(
        {
            HtmlPageArtifactState.DoesNotExist: ERROR_HTML_PAGE_DOES_NOT_EXIST,
            HtmlPageView.DoesNotExist: ERROR_HTML_PAGE_DOES_NOT_EXIST,
        }
    )
    @validate_body(ArtifactRevokeSerializer, return_validated=True)
    def post(self, request, view_id: int, data):
        return Response(
            revoke_artifact(
                user=request.user,
                view_id=view_id,
                reason=data["reason"],
            )
        )


class ArtifactStateView(APIView):
    permission_classes = (IsAuthenticated,)

    @map_exceptions({ViewDoesNotExist: ERROR_HTML_PAGE_DOES_NOT_EXIST})
    def get(self, request, view_id: int):
        view = ViewHandler().get_view_as_user(request.user, view_id, HtmlPageView)
        return Response(artifact_status_for_view(view))
