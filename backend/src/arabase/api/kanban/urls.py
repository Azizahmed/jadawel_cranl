from django.urls import re_path

from .views import KanbanStackRowsView, KanbanViewView

app_name = "arabase.api.kanban"

urlpatterns = [
    re_path(
        r"(?P<view_id>[0-9]+)/$",
        KanbanViewView.as_view(),
        name="view",
    ),
    re_path(
        r"(?P<view_id>[0-9]+)/stacks/(?P<select_option_id>[0-9]+|null)/$",
        KanbanStackRowsView.as_view(),
        name="stack_rows",
    ),
]
