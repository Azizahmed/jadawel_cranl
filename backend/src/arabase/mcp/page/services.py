"""Workspace-scoped operations behind the page-view MCP tools.

Every write goes through ``ViewHandler`` rather than the ORM so the normal
create/update permission checks run and the usual signals fire — an MCP client
gets exactly the authority the user behind the endpoint already has, no more.
"""

from typing import Any, Optional

from django.contrib.auth.models import AbstractUser
from django.db import transaction

from arabase.views.exceptions import HtmlPageViewDoesNotExist
from arabase.views.handler import HtmlPageRevisionHandler
from arabase.views.models import HtmlPageView
from arabase.views.view_types import HtmlPageViewType
from jadawel.contrib.database.api.rows.serializers import serialize_rows_for_response
from jadawel.contrib.database.mcp.services import get_table
from jadawel.contrib.database.views.exceptions import ViewDoesNotExist
from jadawel.contrib.database.views.handler import ViewHandler
from jadawel.core.exceptions import PermissionException
from jadawel.core.models import Workspace

# Enough rows for the model to see the real shape of the data — nulls, select
# option objects, link arrays — without spending its context on a data dump.
SAMPLE_ROW_COUNT = 5


def _get_page_view(
    user: AbstractUser, workspace: Workspace, view_id: int
) -> HtmlPageView:
    """
    :raises HtmlPageViewDoesNotExist: if the view is missing, is not a page view,
        or belongs to a workspace this endpoint does not cover.
    """

    try:
        view = ViewHandler().get_view_as_user(user, view_id, HtmlPageView)
    except (ViewDoesNotExist, PermissionException) as exc:
        # Deliberately the same answer either way: telling an MCP client that a
        # view exists but is off-limits leaks the id space of other workspaces.
        raise HtmlPageViewDoesNotExist(
            f"Page view {view_id} does not exist or is not accessible."
        ) from exc

    # An MCP endpoint is bound to one workspace. `get_view_as_user` only asks
    # whether the user may read the view, and a user is usually in several
    # workspaces, so without this check one endpoint would reach all of them.
    if view.table.database.workspace_id != workspace.id:
        raise HtmlPageViewDoesNotExist(
            f"Page view {view_id} is not in this endpoint's workspace."
        )

    return view


def _view_summary(view: HtmlPageView) -> dict:
    return {
        "view_id": view.id,
        "name": view.name,
        "table_id": view.table_id,
        "is_public": view.public,
        "public_slug": view.slug if view.public else None,
        "has_password": view.public_view_has_password,
        "html_bytes": len(view.html),
        "allow_external_resources": view.allow_external_resources,
        "row_limit": view.row_limit,
    }


def list_page_views(
    user: AbstractUser, workspace: Workspace, table_id: int
) -> list[dict]:
    table = get_table(user, workspace, table_id)
    views = HtmlPageView.objects.filter(table=table, trashed=False).order_by(
        "order", "id"
    )
    return [_view_summary(view) for view in views]


def get_page_view(
    user: AbstractUser,
    workspace: Workspace,
    view_id: int,
    include_rows: bool = True,
    endpoint=None,
) -> dict:
    from arabase.mcp.page.contract import RUNTIME_CONTRACT

    view = _get_page_view(user, workspace, view_id)
    view_type = HtmlPageViewType()

    visible_field_options = view_type.get_visible_field_options_in_order(view)
    fields = [
        {
            "id": field_option.field.id,
            "name": field_option.field.name,
            "type": field_option.field.get_type().type,
            "order": field_option.order,
        }
        for field_option in visible_field_options.select_related("field")
    ]

    artifact_status = None
    protected_output = False
    protected_query_dependency = False
    if endpoint is not None:
        from arabase.mcp.protection.artifact_boundary import (
            artifact_status_for_view,
            protected_output_for_view,
            view_query_uses_protected_fields,
        )

        artifact_status = artifact_status_for_view(view)
        # A protected MCP read may describe the template and schema, but must
        # never hand the model raw HTML or an unmasked row sample.  The page
        # runtime has a separate approval boundary for materialization.
        try:
            protected_output = bool(protected_output_for_view(view, endpoint))
            protected_query_dependency = view_query_uses_protected_fields(
                view, endpoint
            )
        except Exception:
            protected_output = True
            protected_query_dependency = True

    result: dict[str, Any] = {
        **_view_summary(view),
        "html": None if protected_output else view.html,
        "fields": fields,
        "runtime_contract": RUNTIME_CONTRACT,
    }
    if artifact_status is not None:
        result["artifact"] = artifact_status

    if include_rows and protected_query_dependency:
        # Do not execute the view queryset at all: even a masked sample or
        # count would disclose protected membership/order through this page.
        result["row_count"] = None
        result["row_sample"] = []
        return result

    if include_rows:
        model = view.table.get_model()
        queryset = ViewHandler().get_queryset(user, view, model=model)
        row_sample = list(
            serialize_rows_for_response(
                list(queryset[:SAMPLE_ROW_COUNT]), model, user_field_names=True
            )
        )
        if endpoint is not None:
            from types import SimpleNamespace

            from arabase.mcp.protection.artifact_boundary import page_feed_field_ids
            from arabase.mcp.protection.egress import mask_direct_row_output
            from arabase.mcp.protection.policy_state import (
                get_mcp_protection_policy_state,
            )

            # The MCP sample follows the same final egress gateway as row
            # tools.  For a protected artifact, an approval is not needed to
            # show the model a schema/sample; protected cells remain tokens.
            policy = get_mcp_protection_policy_state(endpoint)
            row_sample = mask_direct_row_output(
                endpoint,
                SimpleNamespace(table_id=view.table_id),
                {"results": row_sample},
                policy,
            )["results"]
            try:
                allowed_ids = page_feed_field_ids(
                    view, audience="authenticated", user=user
                )
            except Exception:
                # A pending/revoked artifact is still inspectable by the MCP
                # author as safe metadata and masked sample data; materialized
                # page feeds remain blocked until approval.
                allowed_ids = None
            if allowed_ids is not None:
                allowed_names = {
                    field.name
                    for field in view.table.field_set.filter(id__in=allowed_ids)
                }
                row_sample = [
                    {
                        key: value
                        for key, value in row.items()
                        if key in {"id", "order"} or key in allowed_names
                    }
                    for row in row_sample
                ]
        result["row_count"] = queryset.count()
        result["row_sample"] = row_sample

    return result


@transaction.atomic
def create_page_view(
    user: AbstractUser,
    workspace: Workspace,
    table_id: int,
    name: str,
    html: Optional[str] = None,
    endpoint=None,
    protected_field_ids: Optional[list[int]] = None,
    audience: str = "authenticated",
) -> dict:
    table = get_table(user, workspace, table_id)
    view = ViewHandler().create_view(
        user,
        table,
        HtmlPageViewType.type,
        name=name,
        html="",
    )
    if endpoint is not None and html is not None:
        from arabase.mcp.protection.artifact_boundary import submit_mcp_page_change

        return {
            **submit_mcp_page_change(
                user=user,
                endpoint=endpoint,
                view=view,
                html=html,
                protected_field_ids=protected_field_ids or [],
                audience=audience,
            ),
            **_view_summary(view),
        }
    if html:
        updated = ViewHandler().update_view(user, view, html=html)
        view = updated.updated_view_instance
    return _view_summary(view)


@transaction.atomic
def update_page_view(
    user: AbstractUser,
    workspace: Workspace,
    view_id: int,
    html: Optional[str] = None,
    name: Optional[str] = None,
    allow_external_resources: Optional[bool] = None,
    row_limit: Optional[int] = None,
    endpoint=None,
    protected_field_ids: Optional[list[int]] = None,
    audience: str = "authenticated",
) -> dict:
    view = _get_page_view(user, workspace, view_id)

    values: dict[str, Any] = {}
    if html is not None:
        values["html"] = html
    if name is not None:
        values["name"] = name
    if allow_external_resources is not None:
        values["allow_external_resources"] = allow_external_resources
    if row_limit is not None:
        values["row_limit"] = row_limit

    if not values:
        return _view_summary(view)

    if endpoint is not None and html is not None:
        from arabase.mcp.protection.artifact_boundary import submit_mcp_page_change

        return {
            **submit_mcp_page_change(
                user=user,
                endpoint=endpoint,
                view=view,
                html=html,
                protected_field_ids=protected_field_ids or [],
                audience=audience,
                pending_view_values={
                    key: value for key, value in values.items() if key != "html"
                },
            ),
            **_view_summary(view),
        }

    # Snapshot before the write, and only when the html is actually changing —
    # a rename should not push a version out of the history.
    if html is not None and html != view.html:
        HtmlPageRevisionHandler().snapshot(view, user)

    updated = ViewHandler().update_view(user, view, **values)
    return _view_summary(updated.updated_view_instance)


def list_page_revisions(
    user: AbstractUser, workspace: Workspace, view_id: int
) -> list[dict]:
    view = _get_page_view(user, workspace, view_id)
    return [
        {
            "revision_id": revision.id,
            "created_on": revision.created_on.isoformat(),
            "created_by": (
                revision.created_by.first_name if revision.created_by else None
            ),
            "html_bytes": len(revision.html),
        }
        for revision in view.revisions.all()
    ]


@transaction.atomic
def restore_page_revision(
    user: AbstractUser,
    workspace: Workspace,
    view_id: int,
    revision_id: int,
    endpoint=None,
    protected_field_ids: Optional[list[int]] = None,
    audience: str = "authenticated",
) -> dict:
    view = _get_page_view(user, workspace, view_id)
    handler = HtmlPageRevisionHandler()
    revision = handler.get_revision(view, revision_id)

    if endpoint is not None:
        from arabase.mcp.protection.artifact_boundary import submit_mcp_page_change

        return {
            **submit_mcp_page_change(
                user=user,
                endpoint=endpoint,
                view=view,
                html=revision.html,
                protected_field_ids=protected_field_ids or [],
                audience=audience,
            ),
            **_view_summary(view),
        }

    # Restoring is itself a change worth being able to undo.
    handler.snapshot(view, user)
    updated = ViewHandler().update_view(user, view, html=revision.html)
    return _view_summary(updated.updated_view_instance)
