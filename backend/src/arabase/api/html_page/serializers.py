from rest_framework import serializers

from arabase.views.models import HtmlPageViewFieldOptions, HtmlPageViewRevision


class HtmlPageViewFieldOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HtmlPageViewFieldOptions
        fields = ("hidden", "order")


class HtmlPageViewRevisionSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = HtmlPageViewRevision
        fields = ("id", "created_on", "created_by")

    @staticmethod
    def get_created_by(instance) -> str:
        return instance.created_by.first_name if instance.created_by else ""
