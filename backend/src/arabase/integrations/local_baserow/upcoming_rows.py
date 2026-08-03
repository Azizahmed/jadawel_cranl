from datetime import timedelta
from typing import Any, Dict, Optional

from django.contrib.auth.models import AbstractUser
from django.db.models import F, Q
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from arabase.integrations.local_baserow.models import LocalBaserowUpcomingRows
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.integrations.local_baserow.service_types import (
    LocalBaserowListRowsUserServiceType,
)
from baserow.core.services.dispatch_context import DispatchContext
from baserow.core.services.exceptions import (
    ServiceImproperlyConfiguredDispatchException,
)
from baserow.core.services.types import ServiceSubClass

MAX_DAYS_AHEAD = 365
"""A window wider than a year stops being an agenda, and the row limit would
silently hide most of it anyway."""


class LocalBaserowUpcomingRowsUserServiceType(LocalBaserowListRowsUserServiceType):
    """
    List rows, narrowed to those due within the next `days_ahead` days and
    ordered soonest first.
    """

    type = "local_baserow_upcoming_rows"
    model_class = LocalBaserowUpcomingRows

    @property
    def allowed_fields(self):
        return super().allowed_fields + [
            "date_field",
            "days_ahead",
            "include_overdue",
        ]

    @property
    def serializer_field_names(self):
        return super().serializer_field_names + [
            "date_field_id",
            "days_ahead",
            "include_overdue",
        ]

    @property
    def serializer_field_overrides(self):
        return {
            **super().serializer_field_overrides,
            "date_field_id": serializers.IntegerField(
                required=False,
                allow_null=True,
                help_text="The id of the date field defining when a record is due.",
            ),
        }

    class SerializedDict(LocalBaserowListRowsUserServiceType.SerializedDict):
        date_field_id: int
        days_ahead: int
        include_overdue: bool

    def enhance_queryset(self, queryset):
        return super().enhance_queryset(queryset).select_related("date_field")

    def prepare_values(
        self,
        values: Dict[str, Any],
        user: AbstractUser,
        instance: Optional[ServiceSubClass] = None,
    ) -> Dict[str, Any]:
        values = super().prepare_values(values, user, instance)

        if "table" in values:
            # The date field belongs to the previous table.
            if (
                "date_field_id" not in values
                and instance
                and instance.date_field_id
                and instance.table != values["table"]
            ):
                values["date_field"] = None

        if "days_ahead" in values and values["days_ahead"] is not None:
            days_ahead = values["days_ahead"]
            if days_ahead < 1 or days_ahead > MAX_DAYS_AHEAD:
                raise DRFValidationError(
                    detail=f"days_ahead must be between 1 and {MAX_DAYS_AHEAD}.",
                    code="invalid_days_ahead",
                )

        if "date_field_id" in values:
            date_field_id = values.pop("date_field_id")
            if date_field_id is None:
                values["date_field"] = None
            else:
                field = FieldHandler().get_field(date_field_id)
                table = values.get("table", getattr(instance, "table", None))
                if table is None or field.table_id != table.id:
                    raise DRFValidationError(
                        detail=f"The field with ID {date_field_id} is not related "
                        "to the given table.",
                        code="invalid_field",
                    )
                if not self._is_date_field(field):
                    raise DRFValidationError(
                        detail=f"The field with ID {date_field_id} is not a date "
                        "field.",
                        code="invalid_date_field",
                    )
                values["date_field"] = field

        return values

    @staticmethod
    def _is_date_field(field) -> bool:
        """
        A field can carry a date without being the `date` field type — a created
        on or last modified field is a perfectly reasonable thing to build an
        agenda from — so the test is whether it has date semantics at all.
        """

        specific = field.specific
        field_type = field_type_registry.get_by_model(specific)
        return hasattr(specific, "date_include_time") or field_type.type in (
            "date",
            "created_on",
            "last_modified",
        )

    def export_prepared_values(self, instance: LocalBaserowUpcomingRows) -> dict:
        values = super().export_prepared_values(instance)
        if values.get("date_field"):
            del values["date_field"]
            values["date_field_id"] = instance.date_field_id
        return values

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: Dict[str, Any],
        files_zip=None,
        storage=None,
        cache=None,
        **kwargs,
    ):
        if prop_name == "date_field_id":
            return id_mapping.get("database_fields", {}).get(value, value)

        return super().deserialize_property(
            prop_name,
            value,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
            **kwargs,
        )

    def resolve_service_formulas(
        self,
        service: LocalBaserowUpcomingRows,
        dispatch_context: DispatchContext,
    ) -> Dict[str, Any]:
        if not service.date_field_id:
            raise ServiceImproperlyConfiguredDispatchException(
                "The date field property is missing."
            )

        if service.date_field.trashed:
            raise ServiceImproperlyConfiguredDispatchException(
                f"The field with ID {service.date_field_id} is trashed."
            )

        return super().resolve_service_formulas(service, dispatch_context)

    def get_table_queryset(self, service, table, dispatch_context, model):
        """
        Narrows the queryset to the window and orders it by the date.

        The ordering deliberately replaces any service or view sort: an agenda
        that is not in date order is not an agenda. Filters still apply, so a
        view or service filter can scope the agenda to one assignee or status.
        """

        queryset = super().get_table_queryset(service, table, dispatch_context, model)

        date_field = service.date_field
        db_column = date_field.db_column
        # Comparing a timestamp column against a date would include or exclude a
        # whole day at the boundary depending on the time of day, so datetimes
        # are compared by their date part.
        lookup = f"{db_column}__date" if self._has_time(date_field) else db_column

        today = timezone.localdate()
        window = Q(**{f"{lookup}__lte": today + timedelta(days=service.days_ahead)})
        if not service.include_overdue:
            window &= Q(**{f"{lookup}__gte": today})

        return (
            queryset.filter(window)
            .exclude(**{f"{db_column}__isnull": True})
            .order_by(F(db_column).asc(), "id")
        )

    @staticmethod
    def _has_time(field) -> bool:
        return bool(getattr(field.specific, "date_include_time", False))
