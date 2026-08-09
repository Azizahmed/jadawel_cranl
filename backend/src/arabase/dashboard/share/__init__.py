"""Public link sharing for dashboard applications.

Jadawel's dashboards are private to a workspace. This package adds the same kind
of public link that a form or grid view already has: an owner creates a link,
can rotate it, can put a password on it, and can revoke it. The state lives in
its own :class:`arabase.dashboard.share.models.DashboardShare` row rather than on
``jadawel.contrib.dashboard.models.Dashboard`` so the feature stays additive.
"""
