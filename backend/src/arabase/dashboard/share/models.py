import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from jadawel.contrib.dashboard.models import Dashboard
from jadawel.core.mixins import CreatedAndUpdatedOnMixin, HierarchicalModelMixin


class DashboardShare(HierarchicalModelMixin, CreatedAndUpdatedOnMixin, models.Model):
    """The public link of a single dashboard.

    The row only exists while the dashboard is shared, so ``DashboardShare``
    needs no ``public`` flag: revoking the link deletes the row and the slug is
    gone with it. The field names mirror
    :class:`jadawel.contrib.database.views.models.View` on purpose — the sharing
    UX is meant to be recognisably the same as a shared view.
    """

    dashboard = models.OneToOneField(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="share",
        help_text="The dashboard that is shared through this link.",
    )
    slug = models.SlugField(
        default=secrets.token_urlsafe,
        unique=True,
        db_index=True,
        help_text="The unique slug where the dashboard can be accessed publicly on.",
    )
    public_view_password = models.CharField(
        # Sized for Django's hash output, not for the password the user types.
        max_length=128,
        blank=True,
        help_text="The password required to access the public dashboard URL.",
    )

    class Meta:
        ordering = ("id",)

    def get_parent(self):
        return self.dashboard

    @property
    def has_password(self) -> bool:
        return self.public_view_password != ""  # nosec b105

    @staticmethod
    def create_new_slug() -> str:
        return secrets.token_urlsafe()

    def rotate_slug(self):
        self.slug = DashboardShare.create_new_slug()

    def set_password(self, password: str):
        self.public_view_password = make_password(password)

    def check_public_password(self, password: str) -> bool:
        if not self.has_password:
            return True
        return check_password(password, self.public_view_password)
