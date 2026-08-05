from django.apps import AppConfig


class WSConfig(AppConfig):
    name = "jadawel.ws"

    def ready(self):
        import jadawel.ws.signals  # noqa: F403, F401
