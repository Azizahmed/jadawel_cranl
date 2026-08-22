from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ArabaseConfig(AppConfig):
    """Root AppConfig for the Jadawel fork's additive backend code.

    ``ready()`` is the single place where we hook into Jadawel's registries
    (field types, view types, actions, plugins, permission managers, ...).
    Always prefer a registry hook here over editing a core ``jadawel.*`` file;
    if a core edit is truly unavoidable, log it in ``PATCHES.md``.
    """

    name = "arabase"
    verbose_name = "Arabase (Jadawel)"

    def ready(self):
        # Registry registrations land here as each phase is implemented, e.g.:
        #
        #     from jadawel.contrib.database.fields.registries import field_type_registry
        #     from arabase.fields.hijri import HijriDateFieldType
        #     field_type_registry.register(HijriDateFieldType())
        #
        # Keep imports inside ready() (not at module top) so Django app loading
        # order is respected.
        from arabase.plugins import ArabasePlugin
        from jadawel.core.registries import plugin_registry

        plugin_registry.register(ArabasePlugin())

        from arabase.integrations.local_jadawel.service_types import (
            LocalJadawelGroupedAggregateRowsUserServiceType,
        )
        from arabase.integrations.local_jadawel.upcoming_rows import (
            LocalJadawelUpcomingRowsUserServiceType,
        )
        from jadawel.core.services.registries import service_type_registry

        service_type_registry.register(
            LocalJadawelGroupedAggregateRowsUserServiceType()
        )
        service_type_registry.register(LocalJadawelUpcomingRowsUserServiceType())

        from arabase.dashboard.widgets.widget_types import (
            ChartWidgetType,
            ProgressWidgetType,
            RecordsListWidgetType,
            UpcomingDatesWidgetType,
        )
        from jadawel.contrib.dashboard.widgets.registries import widget_type_registry

        widget_type_registry.register(ChartWidgetType())
        widget_type_registry.register(RecordsListWidgetType())
        widget_type_registry.register(ProgressWidgetType())
        widget_type_registry.register(UpcomingDatesWidgetType())

        from arabase.views.view_types import HtmlPageViewType
        from jadawel.contrib.database.views.registries import view_type_registry

        # Registering is all it takes to mount /api/database/views/html-page/:
        # core builds that urlconf from `view_type_registry.api_urls`.
        view_type_registry.register(HtmlPageViewType())

        from arabase.template_catalog import (
            schedule_local_template_catalog_reconciliation,
        )

        post_migrate.connect(
            schedule_local_template_catalog_reconciliation,
            sender=self,
            dispatch_uid="arabase_reconcile_local_template_catalog",
        )

        from arabase.mcp.page.tools import (
            CreatePageViewMcpTool,
            GetPageViewMcpTool,
            ListPageViewRevisionsMcpTool,
            ListPageViewsMcpTool,
            RestorePageViewRevisionMcpTool,
            UpdatePageViewMcpTool,
        )
        from jadawel.core.mcp.registries import mcp_tool_registry

        # How a page is authored: an AI client drives these instead of Jadawel
        # calling a model itself, so no provider credentials live in the app.
        mcp_tool_registry.register(ListPageViewsMcpTool())
        mcp_tool_registry.register(GetPageViewMcpTool())
        mcp_tool_registry.register(CreatePageViewMcpTool())
        mcp_tool_registry.register(UpdatePageViewMcpTool())
        mcp_tool_registry.register(ListPageViewRevisionsMcpTool())
        mcp_tool_registry.register(RestorePageViewRevisionMcpTool())
