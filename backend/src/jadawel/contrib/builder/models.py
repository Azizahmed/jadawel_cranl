from functools import cached_property

from django.db import models

from jadawel.contrib.builder.domains.models import Domain, PublishDomainJob
from jadawel.contrib.builder.elements.models import Element
from jadawel.contrib.builder.pages.models import Page
from jadawel.contrib.builder.theme.models import (
    ButtonThemeConfigBlock,
    ColorThemeConfigBlock,
    TypographyThemeConfigBlock,
)
from jadawel.core.models import Application, UserFile

__all__ = [
    "Builder",
    "Page",
    "Domain",
    "PublishDomainJob",
    "Element",
    "ColorThemeConfigBlock",
    "TypographyThemeConfigBlock",
    "ButtonThemeConfigBlock",
]


class Builder(Application):
    favicon_file = models.ForeignKey(
        UserFile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="builder_favicon_file",
    )

    login_page = models.OneToOneField(
        Page,
        on_delete=models.SET_NULL,
        help_text="The login page for this application. This is related to the "
        "visibility settings of builder pages.",
        related_name="login_page",
        null=True,
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            from jadawel.contrib.builder.pages.handler import PageHandler

            # Create the shared page
            PageHandler().create_shared_page(self)

    def get_parent(self):
        # If we had select related workspace we want to keep it
        self.application_ptr.workspace = self.workspace
        # Parent is the Application here even if it's at the "same" level
        # but it's a more generic type
        return self.application_ptr

    @property
    def visible_pages(self):
        return self.page_set(manager="objects_without_shared")

    @cached_property
    def shared_page(self):
        from jadawel.contrib.builder.pages.handler import PageHandler

        return PageHandler().get_shared_page(self)

    def get_workspace(self):
        from jadawel.contrib.builder.domains.handler import DomainHandler

        if not self.workspace_id:
            domain = DomainHandler().get_domain_for_builder(self)
            return domain.builder.workspace
        else:
            return self.workspace
