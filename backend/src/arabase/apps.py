from django.apps import AppConfig


class ArabaseConfig(AppConfig):
    """Root AppConfig for the Jadawel fork's additive backend code.

    ``ready()`` is the single place where we hook into Baserow's registries
    (field types, view types, actions, plugins, permission managers, ...).
    Always prefer a registry hook here over editing a core ``baserow.*`` file;
    if a core edit is truly unavoidable, log it in ``PATCHES.md``.
    """

    name = "arabase"
    verbose_name = "Arabase (Jadawel)"

    def ready(self):
        # Registry registrations land here as each phase is implemented, e.g.:
        #
        #     from baserow.contrib.database.fields.registries import field_type_registry
        #     from arabase.fields.hijri import HijriDateFieldType
        #     field_type_registry.register(HijriDateFieldType())
        #
        # Keep imports inside ready() (not at module top) so Django app loading
        # order is respected.
        from arabase.plugins import ArabasePlugin
        from baserow.core.registries import plugin_registry

        plugin_registry.register(ArabasePlugin())
