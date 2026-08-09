class DashboardShareDoesNotExist(Exception):
    """Raised when a dashboard has no public link (or the slug is unknown)."""


class NoAuthorizationToPubliclySharedDashboard(Exception):
    """Raised when a password protected public dashboard is accessed without a
    valid authorization token."""
