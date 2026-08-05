from django.urls import re_path

from jadawel.api.admin.dashboard.views import AdminDashboardView

app_name = "jadawel.api.admin.dashboard"

urlpatterns = [
    re_path(r"^$", AdminDashboardView.as_view(), name="dashboard"),
]
