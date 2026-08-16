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

    result: dict[str, Any] = {
        **_view_summary(view),
        "html": view.html,
        "fields": fields,
        "runtime_contract": RUNTIME_CONTRACT,
    }

    if include_rows:
        model = view.table.get_model()
        queryset = ViewHandler().get_queryset(user, view, model=model)
        result["row_count"] = queryset.count()
        result["row_sample"] = list(
            serialize_rows_for_response(
                list(queryset[:SAMPLE_ROW_COUNT]), model, user_field_names=True
            )
        )

    return result


@transaction.atomic
def create_page_view(
    user: AbstractUser,
    workspace: Workspace,
    table_id: int,
    name: str,
    html: Optional[str] = None,
) -> dict:
    table = get_table(user, workspace, table_id)
    view = ViewHandler().create_view(
        user,
        table,
        HtmlPageViewType.type,
        name=name,
        html=html or "",
    )
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
    user: AbstractUser, workspace: Workspace, view_id: int, revision_id: int
) -> dict:
    view = _get_page_view(user, workspace, view_id)
    handler = HtmlPageRevisionHandler()
    revision = handler.get_revision(view, revision_id)

    # Restoring is itself a change worth being able to undo.
    handler.snapshot(view, user)
    updated = ViewHandler().update_view(user, view, html=revision.html)
    return _view_summary(updated.updated_view_instance)
