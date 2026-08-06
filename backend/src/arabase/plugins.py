from django.urls import include, path

from jadawel.core.registries import Plugin


class ArabasePlugin(Plugin):
    """Mount point for the Jadawel fork's own API routes.

    Baserow's `plugin_registry` contributes its members' urls to the root
    urlconf, so registering here adds `/api/arabase/...` without editing
    `jadawel/config/urls.py` or `jadawel/api/urls.py`. Keeping our routes on a
    separate prefix also means an upstream route can never collide with ours.
    """

    type = "arabase"

    def get_api_urls(self):
        return [
            path(
                "arabase/",
                include("arabase.api.urls", namespace=self.type),
            ),
        ]
