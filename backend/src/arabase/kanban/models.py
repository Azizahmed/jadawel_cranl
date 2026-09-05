from django.db import models

from jadawel.contrib.database.fields.models import Field
from jadawel.contrib.database.views.models import View
from jadawel.core.models import HierarchicalModelMixin


class KanbanView(View):
    """A board view: one column per option of a single select field.

    The fork's OSS re-implementation of upstream's premium kanban view,
    written from scratch. It is a real `View`, so the generic view CRUD,
    filters, sorts and decorations (`can_decorate`) all work through core's
    machinery — including the base `View.get_field_options`, which resolves
    the options model through the view type registry. Rows are fetched per
    column by the view type's own API (`arabase.api.kanban`).
    """

    # Nullable on purpose: a view can be created before the user has chosen
    # a field to group by, in which case the client shows a picker instead
    # of an empty board that looks broken.
    single_select_field = models.ForeignKey(
        Field,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="kanban_view_single_select_field",
        help_text="The single select field whose options become the board's columns.",
    )
    card_cover_image_field = models.ForeignKey(
        Field,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="kanban_view_card_cover_field",
        help_text="Optional file field whose first image is shown as the card cover.",
    )


class KanbanViewFieldOptionsManager(models.Manager):
    """A trashed view keeps its field options, so filter them out here.

    Mirrors ``GalleryViewFieldOptionsManager``.
    """

    def get_queryset(self):
        trashed_Q = models.Q(kanban_view__trashed=True) | models.Q(field__trashed=True)
        return super().get_queryset().filter(~trashed_Q)


class KanbanViewFieldOptions(HierarchicalModelMixin, models.Model):
    objects = KanbanViewFieldOptionsManager()
    objects_and_trash = models.Manager()

    kanban_view = models.ForeignKey(KanbanView, on_delete=models.CASCADE)
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    hidden = models.BooleanField(
        default=True,
        help_text="Whether the field is shown on the kanban cards.",
    )
    # The default value is the maximum value of the small integer field because
    # a newly created field must always be last.
    order = models.SmallIntegerField(
        default=32767,
        help_text="The order that the field has on the kanban cards. Lower value is "
        "first.",
    )

    def get_parent(self):
        return self.kanban_view

    class Meta:
        ordering = ("order", "field_id")
        unique_together = ("kanban_view", "field")
