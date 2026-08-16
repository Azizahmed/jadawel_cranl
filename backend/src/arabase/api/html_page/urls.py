from django.urls import re_path

from .views import HtmlPageViewRowsView, PublicHtmlPageViewRowsView

app_name = "arabase.api.html_page"

urlpatterns = [
    re_path(
        r"(?P<view_id>[0-9]+)/$",
        HtmlPageViewRowsView.as_view(),
        name="list",
    ),
    re_path(
        r"(?P<slug>[-\w]+)/public/rows/$",
        PublicHtmlPageViewRowsView.as_view(),
        name="public_rows",
    ),
]
