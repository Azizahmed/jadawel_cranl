from typing import List

from django.contrib.contenttypes.models import ContentType

import pytest

from jadawel.core.exceptions import InstanceTypeDoesNotExist
from jadawel.core.user_sources.models import UserSource
from jadawel.core.user_sources.registries import (
    UserSourceType,
    user_source_type_registry,
)


class UserSourceFixtures:
    def _get_user_source_type_or_skip(self, type_name=None):
        """Return a concrete user-source type or skip in the OSS-only fork.

        Jadawel's only concrete user-source implementation is supplied by the
        deleted enterprise package. The generic core fixtures are still useful
        when a downstream package registers a type, but they cannot construct a
        model in this OSS-only repository by themselves.
        """

        if type_name is not None:
            try:
                return user_source_type_registry.get(type_name)
            except InstanceTypeDoesNotExist:
                pytest.skip(
                    f"User-source type {type_name!r} is not available in the "
                    "OSS-only Jadawel build."
                )

        user_source_type = next(iter(user_source_type_registry.get_all()), None)
        if user_source_type is None:
            pytest.skip(
                "No concrete user-source type is available in the OSS-only "
                "Jadawel build."
            )
        return user_source_type

    def create_user_source_with_first_type(self, **kwargs):
        first_user_source_type = self._get_user_source_type_or_skip()
        return self.create_user_source(first_user_source_type.model_class, **kwargs)

    def create_user_source(self, model_class, user=None, application=None, **kwargs):
        if not application:
            if user is None:
                user = self.create_user()

            application_args = kwargs.pop("application_args", {})
            application = self.create_builder_application(user=user, **application_args)

        if "order" not in kwargs:
            kwargs["order"] = model_class.get_last_order(application)

        kwargs["content_type"] = ContentType.objects.get_for_model(model_class)
        user_source = model_class.objects.create(application=application, **kwargs)

        user_source.uid = user_source.get_type().gen_uid(user_source)
        user_source.save()

        return user_source

    def create_user_sources_with_primary_keys(
        self, user_source_type: UserSourceType, primary_keys: List[int], **kwargs
    ) -> List[UserSource]:
        user_sources = []
        for user_source_id in primary_keys:
            user_source = self.create_user_source(
                user_source_type.model_class, id=user_source_id, **kwargs
            )
            user_sources.append(user_source)
        return user_sources

    def create_user_table_and_role(self, user, builder, user_role, integration=None):
        """Helper to create a User table with a particular user role."""

        # Create the user table for the user_source
        user_table, user_fields, user_rows = self.build_table(
            user=user,
            columns=[
                ("Email", "text"),
                ("Name", "text"),
                ("Password", "text"),
                ("Role", "text"),
            ],
            rows=[
                ["foo@bar.com", "Foo User", "secret", user_role],
            ],
        )
        email_field, name_field, password_field, role_field = user_fields

        integration = integration or self.create_local_jadawel_integration(
            user=user, application=builder
        )
        user_source = self.create_user_source(
            self._get_user_source_type_or_skip("local_jadawel").model_class,
            application=builder,
            integration=integration,
            table=user_table,
            email_field=email_field,
            name_field=name_field,
            role_field=role_field,
        )

        return user_source, integration

    def create_local_jadawel_table_user_source(
        self, application=None, integration=None, table=None, user=None, **kwargs
    ):
        if not application:
            if user is None:
                user = self.create_user()
            application_args = kwargs.pop("application_args", {})
            application = self.create_builder_application(user=user, **application_args)

        if not integration:
            integration = self.create_local_jadawel_integration(application=application)

        if not table:
            table, fields, rows = self.build_table(
                user=user,
                columns=[
                    ("Email", "text"),
                    ("Name", "text"),
                    ("Role", "text"),
                ],
                rows=[
                    ["bram@jadawl.site", "Bram", ""],
                    ["jrmi@jadawl.site", "Jérémie", ""],
                    ["peter@jadawl.site", "Peter", ""],
                    ["tsering@jadawl.site", "Tsering", ""],
                    ["evren@jadawl.site", "Evren", ""],
                ],
            )
            email_field, name_field, role_field = fields
        else:
            email_field = table.field_set.get(name="Email")
            name_field = table.field_set.get(name="Name")
            role_field = table.field_set.get(name="Role")

        local_jadawel_user_source_type = self._get_user_source_type_or_skip(
            "local_jadawel"
        )
        return self.create_user_source(
            local_jadawel_user_source_type.model_class,
            application=application,
            integration=integration,
            table=table,
            email_field=email_field,
            name_field=name_field,
            role_field=role_field,
        )
