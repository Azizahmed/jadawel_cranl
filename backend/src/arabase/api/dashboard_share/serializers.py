from rest_framework import serializers

from arabase.dashboard.share.models import DashboardShare
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


class UpdateDashboardSharePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        required=True,
        allow_null=True,
        allow_blank=False,
        max_length=256,
        trim_whitespace=False,
        help_text=(
            "The password to protect the public link with, or null to remove the "
            "existing password."
        ),
    )


class PublicDashboardAuthSerializer(serializers.Serializer):
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
