"""Reading a date field's *column*, rather than its display settings.

Two widgets bucket and window rows by a date, and both got the same thing wrong
in the same way: they asked ``date_include_time``.

That attribute controls whether the interface shows a time, not what the
database stores. ``created_on`` and ``last_modified`` always store a
``timestamptz`` — ``CreatedOnLastModifiedBaseFieldType.get_model_field`` emits
one regardless — so a field with the time hidden still holds one. Group by it
and the raw timestamp becomes the bucket, one per microsecond; window against
it and Django coerces the comparison date to midnight, silently dropping the
last day.

The column type is the honest test, so it lives here and both callers use it.
"""

from zoneinfo import ZoneInfo

from django.core.exceptions import FieldDoesNotExist
from django.db import models


def is_datetime_column(model, field) -> bool:
    """Whether the field's database column carries a time as well as a date.

    :param model: The generated table model the field belongs to.
    :param field: The `Field` instance, specific or not.
    """

    specific = getattr(field, "specific", field)
    db_column = getattr(field, "db_column", None)
    if model is None or not db_column:
        return bool(getattr(specific, "date_include_time", False))

    try:
        model_field = model._meta.get_field(db_column)
    except (FieldDoesNotExist, AttributeError):
        # A trashed or otherwise absent column: fall back to the display flag
        # rather than raising in the middle of a dispatch.
        return bool(getattr(specific, "date_include_time", False))

    # `DateTimeField` subclasses `DateField`, so the order of this test matters:
    # a plain date column must not answer True.
    return isinstance(model_field, models.DateTimeField)


def field_tzinfo(field):
    """The timezone a date field's values should be read in, or None.

    A window or a bucket computed in UTC lands a day early for anyone east of
    it — for Riyadh at UTC+3, every night between midnight and 03:00. When the
    field pins a timezone, honour it; otherwise leave Django's default alone,
    which is what every existing deployment already sees.
    """

    name = getattr(field, "date_force_timezone", None) or getattr(
        getattr(field, "specific", None), "date_force_timezone", None
    )
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return None
