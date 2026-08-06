from jadawel.contrib.builder.data_sources.models import DataSource
from jadawel.contrib.integrations.local_jadawel.models import (
    LocalJadawelGetRow,
    LocalJadawelListRows,
)


class DataSourceFixtures:
    def create_builder_local_jadawel_get_row_data_source(self, **kwargs):
        return self.create_builder_data_source(
            service_model_class=LocalJadawelGetRow, **kwargs
        )

    def create_builder_local_jadawel_list_rows_data_source(self, **kwargs):
        return self.create_builder_data_source(
            service_model_class=LocalJadawelListRows, **kwargs
        )

    def create_builder_data_source(
        self,
        page=None,
        user=None,
        service_model_class=None,
        order=None,
        name=None,
        **kwargs,
    ):
        if not page:
            if user is None:
                user = self.create_user()

            builder = kwargs.pop("builder", None)
            page_args = kwargs.pop("page_args", {})
            page = self.create_builder_page(user=user, builder=builder, **page_args)

        service = kwargs.pop("service", None)
        if service is None and service_model_class:
            integrations_args = kwargs.pop("integration_args", {})
            integrations_args["application"] = page.builder
            service = self.create_service(
                service_model_class, integration_args=integrations_args, **kwargs
            )

        if order is None:
            order = DataSource.get_last_order(page)

        if name is None:
            name = self.fake.unique.word()

        data_source = DataSource.objects.create(
            page=page, name=name, service=service, order=order
        )

        return data_source
