from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from arabase.dashboard.share.models import DashboardShare
from jadawel.api.services.serializers import PublicServiceSerializer
from jadawel.contrib.dashboard.models import Dashboard


class DashboardShareSerializer(serializers.ModelSerializer):
    """What the owner of a dashboard sees in the sharing menu."""

    has_password = serializers.BooleanField(
        read_only=True,
        help_text="Whether a password is required to open the public link.",
    )

    class Meta:
        model = DashboardShare
        fields = ("dashboard_id", "slug", "has_password")
        extra_kwargs = {
            "dashboard_id": {"read_only": True},
            "slug": {"read_only": True},
        }


MIN_SHARE_PASSWORD_LENGTH = 8
"""A share password is the only thing standing between a link and its data, and
it is guessed offline-fast against a hash. Anything shorter is not a control."""


class UpdateDashboardSharePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        required=True,
        allow_null=True,
        allow_blank=False,
        min_length=MIN_SHARE_PASSWORD_LENGTH,
        max_length=256,
        trim_whitespace=False,
        help_text=(
            "The password to protect the public link with, or null to remove the "
            "existing password."
        ),
    )


class PublicDashboardAuthSerializer(serializers.Serializer):
    # Deliberately not length-checked: this is the guess, not the policy, and
    # rejecting a short one early would confirm the shape of the real password.
    password = serializers.CharField(
        required=True, max_length=256, trim_whitespace=False
    )


class PublicDashboardAuthResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(
        help_text=(
            "Send this token in the `Jadawel-View-Authorization` header to open the "
            "password protected dashboard."
        )
    )


class PublicDashboardSerializer(serializers.ModelSerializer):
    """The dashboard itself as an anonymous visitor sees it.

    Deliberately narrow: a visitor gets what is rendered on the page (name and
    description) and nothing that identifies the workspace it lives in.
    """

    class Meta:
        model = Dashboard
        fields = ("id", "name", "description")
        extra_kwargs = {
            "id": {"read_only": True},
            "name": {"read_only": True},
            "description": {"read_only": True},
        }


class PublicDashboardDataSourceSerializer(PublicServiceSerializer):
    """A data source as an anonymous visitor sees it.

    The authenticated serializer flattens the whole service onto the data
    source, which for a visitor means the table and view it reads, the
    integration behind it, its filters, its search query and its sample data —
    none of which is rendered, and all of which describes the workspace the
    dashboard was built in.

    What a visitor's page actually needs is the id to dispatch, the type to
    pick a component, and the schema to name the columns. `date_field_id` joins
    them because the agenda widget renders the due date in a column of its own.

    The schema is narrowed by `allowed_fields` in the serializer context, so a
    visitor is not told the names of columns they cannot fetch.
    """

    id = serializers.SerializerMethodField(help_text="Data source id.")
    name = serializers.SerializerMethodField(help_text="The data source's name.")
    dashboard_id = serializers.SerializerMethodField(
        help_text="The dashboard this data source belongs to."
    )
    order = serializers.SerializerMethodField(help_text="Lowest first.")
    date_field_id = serializers.SerializerMethodField(
        help_text="The date field an agenda widget renders, if the service has one."
    )

    @extend_schema_field(OpenApiTypes.INT)
    def get_id(self, instance):
        return self.context["data_source"].id

    @extend_schema_field(OpenApiTypes.STR)
    def get_name(self, instance):
        return self.context["data_source"].name

    @extend_schema_field(OpenApiTypes.INT)
    def get_dashboard_id(self, instance):
        return self.context["data_source"].dashboard_id

    @extend_schema_field(OpenApiTypes.STR)
    def get_order(self, instance):
        return str(self.context["data_source"].order)

    @extend_schema_field(OpenApiTypes.INT)
    def get_date_field_id(self, instance):
        return getattr(instance.specific, "date_field_id", None)

    class Meta(PublicServiceSerializer.Meta):
        fields = (
            "id",
            "type",
            "schema",
            "name",
            "dashboard_id",
            "order",
            "date_field_id",
        )
        extra_kwargs = {
            "type": {"read_only": True},
            "schema": {"read_only": True},
        }
