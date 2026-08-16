from typing import Optional

from django.contrib.auth.models import AbstractUser

from arabase.views.constants import MAX_REVISIONS
from arabase.views.exceptions import HtmlPageViewRevisionDoesNotExist
from arabase.views.models import HtmlPageView, HtmlPageViewRevision


class HtmlPageRevisionHandler:
    """Keeps a short undo history for a page's HTML.

    Pages are written by a model over MCP, which makes a destructive overwrite a
    normal-looking tool call rather than an obvious mistake. Snapshotting the
    *previous* html before each change means the recovery path is a single tool
    call instead of a database restore.
    """

    def snapshot(
        self,
        view: HtmlPageView,
        user: Optional[AbstractUser] = None,
    ) -> Optional[HtmlPageViewRevision]:
        """Record the page's current html, then trim to the newest N.

        Returns ``None`` for a page that has no html yet — there is nothing to
        go back to, and a row of empty string is noise in the history.
        """

        if not view.html:
            return None

        revision = HtmlPageViewRevision.objects.create(
            html_page_view=view,
            html=view.html,
            created_by=user if user and user.is_authenticated else None,
        )
        self._trim(view)
        return revision

    def _trim(self, view: HtmlPageView):
        keep_ids = list(
            HtmlPageViewRevision.objects.filter(html_page_view=view)
            .order_by("-created_on", "-id")
            .values_list("id", flat=True)[:MAX_REVISIONS]
        )
        HtmlPageViewRevision.objects.filter(html_page_view=view).exclude(
            id__in=keep_ids
        ).delete()

    def get_revision(self, view: HtmlPageView, revision_id: int):
        """
        :raises HtmlPageViewRevisionDoesNotExist: if the revision is missing or
            belongs to another page.
        """

        try:
            return HtmlPageViewRevision.objects.get(id=revision_id, html_page_view=view)
        except HtmlPageViewRevision.DoesNotExist as exc:
            raise HtmlPageViewRevisionDoesNotExist(
                f"Revision {revision_id} does not exist for this page view."
            ) from exc
