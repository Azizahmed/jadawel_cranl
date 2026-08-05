from jadawel.contrib.integrations.core.models import SMTPIntegration
from jadawel.core.integrations.registries import IntegrationType
from jadawel.core.integrations.types import IntegrationDict


class SMTPIntegrationType(IntegrationType):
    type = "smtp"
    model_class = SMTPIntegration

    class SerializedDict(IntegrationDict):
        host: str
        port: int
        use_tls: bool
        username: str
        password: str

    serializer_field_names = ["host", "port", "use_tls", "username", "password"]
    allowed_fields = ["host", "port", "use_tls", "username", "password"]
    sensitive_fields = ["host", "port", "use_tls", "username", "password"]

    request_serializer_field_names = ["host", "port", "use_tls", "username", "password"]
    request_serializer_field_overrides = {}
