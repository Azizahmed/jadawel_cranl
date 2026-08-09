"""Owner-facing endpoints for the public link of a dashboard.

Mounted under ``/api/arabase/dashboard/<dashboard_id>/share/``. Every method
requires the permission to update the application, which is the same bar the
frontend uses to decide whether to render the sharing menu at all.
"""

from django.db import transaction

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from arabase.api.dashboard_share.errors import ERROR_DASHBOARD_SHARE_DOES_NOT_EXIST
from arabase.api.dashboard_share.serializers import (
    DashboardShareSerializer,
    UpdateDashboardSharePasswordSerializer,
)
from arabase.dashboard.share.exceptions import DashboardShareDoesNotExist
from arabase.dashboard.share.handler import DashboardShareHandler
from jadawel.api.decorators import map_exceptions, validate_body
from jadawel.api.schemas import get_error_schema
from jadawel.contrib.dashboard.api.errors import ERROR_DASHBOARD_DOES_NOT_EXIST
from jadawel.contrib.dashboard.exceptions import DashboardDoesNotExist
from jadawel.contrib.dashboard.handler import DashboardHandler
from jadawel.contrib.dashboard.models import Dashboard
from jadawel.core.handler import CoreHandler
from jadawel.core.operations import UpdateApplicationOperationType

DASHBOARD_ID_PARAMETER = OpenApiParameter(
    name="dashboard_id",
    location=OpenApiParameter.PATH,
    type=OpenApiTypes.INT,
    description="The dashboard to manage the public link of.",
)

SHARE_ERRORS = get_error_schema(
    ["ERROR_DASHBOARD_DOES_NOT_EXIST", "ERROR_DASHBOARD_SHARE_DOES_NOT_EXIST"]
)


def _get_dashboard_for_sharing(request: Request, dashboard_id: int) -> Dashboard:
    dashboard = DashboardHandler().get_dashboard(dashboard_id)
    CoreHandler().check_permissions(
        request.user,
        UpdateApplicationOperationType.type,
        workspace=dashboard.workspace,
        context=dashboard,
    )
    return dashboard


class DashboardShareView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[DASHBOARD_ID_PARAMETER],
        tags=["Arabase dashboard sharing"],
        operation_id="get_dashboard_share",
        description=(
            "Returns the public link of the dashboard. Responds with 404 when the "
            "dashboard is not shared."
        ),
        responses={
            200: DashboardShareSerializer,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: SHARE_ERRORS,
        },
    )
    @map_exceptions(
        {
            DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST,
            DashboardShareDoesNotExist: ERROR_DASHBOARD_SHARE_DOES_NOT_EXIST,
        }
    )
    def get(self, request: Request, dashboard_id: int) -> Response:
        dashboard = _get_dashboard_for_sharing(request, dashboard_id)
        share = DashboardShareHandler().get_share(dashboard)
        return Response(DashboardShareSerializer(share).data)

    @extend_schema(
        parameters=[DASHBOARD_ID_PARAMETER],
        tags=["Arabase dashboard sharing"],
        operation_id="create_dashboard_share",
        description=(
            "Shares the dashboard through a public link. Returns the existing link "
            "if the dashboard is already shared."
        ),
        request=None,
        responses={
            200: DashboardShareSerializer,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: get_error_schema(["ERROR_DASHBOARD_DOES_NOT_EXIST"]),
        },
    )
    @transaction.atomic
    @map_exceptions({DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST})
    def post(self, request: Request, dashboard_id: int) -> Response:
        dashboard = _get_dashboard_for_sharing(request, dashboard_id)
        share = DashboardShareHandler().create_share(dashboard)
        return Response(DashboardShareSerializer(share).data)

    @extend_schema(
        parameters=[DASHBOARD_ID_PARAMETER],
        tags=["Arabase dashboard sharing"],
        operation_id="delete_dashboard_share",
        description=(
            "Revokes the public link. The slug is destroyed, so re-sharing the "
            "dashboard later produces a new URL."
        ),
        request=None,
        responses={
            204: None,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: get_error_schema(["ERROR_DASHBOARD_DOES_NOT_EXIST"]),
        },
    )
    @transaction.atomic
    @map_exceptions({DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST})
    def delete(self, request: Request, dashboard_id: int) -> Response:
        dashboard = _get_dashboard_for_sharing(request, dashboard_id)
        DashboardShareHandler().delete_share(dashboard)
        return Response(status=204)


class DashboardShareRotateSlugView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[DASHBOARD_ID_PARAMETER],
        tags=["Arabase dashboard sharing"],
        operation_id="rotate_dashboard_share_slug",
        description=(
            "Generates a new slug for the public link, which immediately "
            "invalidates the previous URL and every password token handed out for "
            "it."
        ),
        request=None,
        responses={
            200: DashboardShareSerializer,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: SHARE_ERRORS,
        },
    )
    @transaction.atomic
    @map_exceptions(
        {
            DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST,
            DashboardShareDoesNotExist: ERROR_DASHBOARD_SHARE_DOES_NOT_EXIST,
        }
    )
    def post(self, request: Request, dashboard_id: int) -> Response:
        dashboard = _get_dashboard_for_sharing(request, dashboard_id)
        handler = DashboardShareHandler()
        share = handler.rotate_slug(handler.get_share(dashboard))
        return Response(DashboardShareSerializer(share).data)


class DashboardSharePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[DASHBOARD_ID_PARAMETER],
        tags=["Arabase dashboard sharing"],
        operation_id="update_dashboard_share_password",
        description=(
            "Sets the password that protects the public link, or removes it by "
            "sending a null password."
        ),
        request=UpdateDashboardSharePasswordSerializer,
        responses={
            200: DashboardShareSerializer,
            400: get_error_schema(["ERROR_REQUEST_BODY_VALIDATION"]),
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: SHARE_ERRORS,
        },
    )
    @transaction.atomic
    @map_exceptions(
        {
            DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST,
            DashboardShareDoesNotExist: ERROR_DASHBOARD_SHARE_DOES_NOT_EXIST,
        }
    )
    @validate_body(UpdateDashboardSharePasswordSerializer, return_validated=True)
    def patch(self, request: Request, data: dict, dashboard_id: int) -> Response:
        dashboard = _get_dashboard_for_sharing(request, dashboard_id)
        handler = DashboardShareHandler()
        share = handler.set_password(handler.get_share(dashboard), data["password"])
        return Response(DashboardShareSerializer(share).data)
