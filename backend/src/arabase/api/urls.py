from django.urls import re_path

from arabase.api.contact import ContactFormView
from arabase.api.dashboard_share.public import (
    PublicDashboardAuthView,
    PublicDashboardDispatchView,
    PublicDashboardInfoView,
)
from arabase.api.dashboard_share.views import (
    DashboardSharePasswordView,
    DashboardShareRotateSlugView,
    DashboardShareView,
)
from arabase.api.views import WorkspaceActivityView, WorkspaceDatabaseStatsView

app_name = "arabase.api"

urlpatterns = [
    re_path(
        r"^contact/$",
        ContactFormView.as_view(),
        name="contact_form",
    ),
    re_path(
        r"^workspace/(?P<workspace_id>[0-9]+)/database-stats/$",
        WorkspaceDatabaseStatsView.as_view(),
        name="workspace_database_stats",
    ),
    re_path(
        r"^workspace/(?P<workspace_id>[0-9]+)/activity/$",
        WorkspaceActivityView.as_view(),
        name="workspace_activity",
    ),
    re_path(
        r"^dashboard/(?P<dashboard_id>[0-9]+)/share/$",
        DashboardShareView.as_view(),
        name="dashboard_share",
    ),
    re_path(
        r"^dashboard/(?P<dashboard_id>[0-9]+)/share/rotate-slug/$",
        DashboardShareRotateSlugView.as_view(),
        name="dashboard_share_rotate_slug",
    ),
    re_path(
        r"^dashboard/(?P<dashboard_id>[0-9]+)/share/password/$",
        DashboardSharePasswordView.as_view(),
        name="dashboard_share_password",
    ),
    re_path(
        r"^public/dashboard/(?P<slug>[-\w]+)/$",
        PublicDashboardInfoView.as_view(),
        name="public_dashboard",
    ),
    re_path(
        r"^public/dashboard/(?P<slug>[-\w]+)/auth/$",
        PublicDashboardAuthView.as_view(),
        name="public_dashboard_auth",
    ),
    re_path(
        r"^public/dashboard/(?P<slug>[-\w]+)/dispatch/(?P<data_source_id>[0-9]+)/$",
        PublicDashboardDispatchView.as_view(),
        name="public_dashboard_dispatch",
    ),
]
