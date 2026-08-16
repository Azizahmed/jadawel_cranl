from django.conf import settings
from django.db import models
from django.db.models import Q

from arabase.views.constants import DEFAULT_ROW_LIMIT
from jadawel.contrib.database.fields.models import Field
from jadawel.contrib.database.views.models import View
from jadawel.core.mixins import CreatedAndUpdatedOnMixin, HierarchicalModelMixin


class HtmlPageView(View):
    """A view whose body is an HTML document rather than a built-in layout.

    The document is authored by an AI over MCP (see ``arabase.mcp.page``) and is
    rendered inside a sandboxed iframe, never on the app's own origin. It is a
    real view, so it inherits filters, sorts and — via ``View`` — the public slug
    and password that make ``can_share`` work exactly like a form's.
    """

    field_options = models.ManyToManyField(Field, through="HtmlPageViewFieldOptions")
    html = models.TextField(
        blank=True,
        help_text="The HTML document that is rendered for this view.",
    )
    allow_external_resources = models.BooleanField(
        default=False,
        db_default=False,
        help_text=(
            "When true the page may load scripts, styles and fonts from the "
            "configured CDN allowlist. Network requests from the page stay "
            "blocked either way."
        ),
    )
    row_limit = models.PositiveIntegerField(
        default=DEFAULT_ROW_LIMIT,
        db_default=DEFAULT_ROW_LIMIT,
        help_text="How many rows are handed to the page when it renders.",
    )


class HtmlPageViewFieldOptionsManager(models.Manager):
    """A trashed view keeps its field options, so filter them out here.

    Mirrors ``GalleryViewFieldOptionsManager``.
    """

    def get_queryset(self):
        trashed_Q = Q(html_page_view__trashed=True) | Q(field__trashed=True)
        return super().get_queryset().filter(~trashed_Q)


class HtmlPageViewFieldOptions(HierarchicalModelMixin, models.Model):
    objects = HtmlPageViewFieldOptionsManager()
    objects_and_trash = models.Manager()

    html_page_view = models.ForeignKey(HtmlPageView, on_delete=models.CASCADE)
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    # Unlike the gallery's card, a page is code written against the row shape:
    # the author is better served by every field being present and hiding the
    # ones they do not want than by having to reveal each one first.
    hidden = models.BooleanField(
        default=False,
        help_text="Whether the field is withheld from the page's data feed.",
    )
    # The default is the maximum value of the small integer field because a
    # newly created field must always sort last.
    order = models.SmallIntegerField(
        default=32767,
        help_text="The order the field has in the page's data feed. Lower is first.",
    )

    def get_parent(self):
        return self.html_page_view

    class Meta:
        ordering = ("order", "field_id")
        unique_together = ("html_page_view", "field")


class HtmlPageViewRevision(
    HierarchicalModelMixin, CreatedAndUpdatedOnMixin, models.Model
):
    """A previous version of a page's HTML.

    Only the last :data:`~arabase.views.constants.MAX_REVISIONS` are kept. The
    author is nullable because a revision outlives the account that wrote it.
    """

    html_page_view = models.ForeignKey(
        HtmlPageView,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    html = models.TextField(
        blank=True,
        help_text="The HTML this page had before the change that created this row.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="The user who replaced this version, if they still exist.",
    )

    def get_parent(self):
        return self.html_page_view

    class Meta:
        ordering = ("-created_on", "-id")
