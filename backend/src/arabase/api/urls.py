from django.urls import re_path

from arabase.api.contact import ContactFormView
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
]
