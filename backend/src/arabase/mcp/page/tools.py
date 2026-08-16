from arabase.mcp.page import services
from arabase.mcp.page.schemas import (
    CreatePageViewInput,
    GetPageViewInput,
    ListPageViewRevisionsInput,
    ListPageViewsInput,
    RestorePageViewRevisionInput,
    UpdatePageViewInput,
)
from jadawel.core.mcp.models import MCPEndpoint
from jadawel.core.mcp.registries import MCPTool


class ListPageViewsMcpTool(MCPTool):
    """
    List the HTML page views of a table, with their share state and size.
    A page view renders an HTML document you write, showing the table's data.
    """

    type = "list_page_views"
    input_schema = ListPageViewsInput

    def _sync_call(self, endpoint: MCPEndpoint, args: ListPageViewsInput) -> list[dict]:
        return services.list_page_views(
            endpoint.user, endpoint.workspace, args.table_id
        )


class GetPageViewMcpTool(MCPTool):
    """
    Read a page view: its current HTML, the fields it exposes, a sample of its
    rows, and the runtime contract. Always call this before writing or editing a
    page — the returned 'runtime_contract' explains how the page receives data
    and what the sandbox blocks, and code written without reading it will fail.
    """

    type = "get_page_view"
    input_schema = GetPageViewInput

    def _sync_call(self, endpoint: MCPEndpoint, args: GetPageViewInput) -> dict:
        return services.get_page_view(
            endpoint.user, endpoint.workspace, args.view_id, args.include_rows
        )


class CreatePageViewMcpTool(MCPTool):
    """
    Create an HTML page view on a table. Returns the new view's id, which you
    then pass to get_page_view to read the runtime contract before writing the
    document with update_page_view.
    """

    type = "create_page_view"
    input_schema = CreatePageViewInput

    def _sync_call(self, endpoint: MCPEndpoint, args: CreatePageViewInput) -> dict:
        return services.create_page_view(
            endpoint.user,
            endpoint.workspace,
            args.table_id,
            args.name,
            args.html,
        )


class UpdatePageViewMcpTool(MCPTool):
    """
    Replace a page view's HTML document, or change its name, row limit or
    external-resource setting. The html argument overwrites the whole document
    rather than patching it; the previous version is kept as a revision.
    """

    type = "update_page_view"
    input_schema = UpdatePageViewInput

    def _sync_call(self, endpoint: MCPEndpoint, args: UpdatePageViewInput) -> dict:
        return services.update_page_view(
            endpoint.user,
            endpoint.workspace,
            args.view_id,
            html=args.html,
            name=args.name,
            allow_external_resources=args.allow_external_resources,
            row_limit=args.row_limit,
        )


class ListPageViewRevisionsMcpTool(MCPTool):
    """
    List the saved previous versions of a page view's HTML, newest first.
    Use this to find the revision to hand to restore_page_view_revision.
    """

    type = "list_page_view_revisions"
    input_schema = ListPageViewRevisionsInput

    def _sync_call(
        self, endpoint: MCPEndpoint, args: ListPageViewRevisionsInput
    ) -> list[dict]:
        return services.list_page_revisions(
            endpoint.user, endpoint.workspace, args.view_id
        )


class RestorePageViewRevisionMcpTool(MCPTool):
    """
    Roll a page view's HTML back to an earlier revision. The version being
    replaced is itself saved as a revision, so a restore can be undone.
    """

    type = "restore_page_view_revision"
    input_schema = RestorePageViewRevisionInput

    def _sync_call(
        self, endpoint: MCPEndpoint, args: RestorePageViewRevisionInput
    ) -> dict:
        return services.restore_page_revision(
            endpoint.user, endpoint.workspace, args.view_id, args.revision_id
        )
