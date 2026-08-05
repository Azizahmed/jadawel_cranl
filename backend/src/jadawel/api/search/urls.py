from django.urls import path

from jadawel.api.search.views import WorkspaceSearchView

app_name = "jadawel.api.search"

urlpatterns = [
    path(
        "workspace/<int:workspace_id>/",
        WorkspaceSearchView.as_view(),
        name="workspace_search",
    ),
]
