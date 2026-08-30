from django.db.models.signals import post_save

from arabase.mcp.protection.models import MCPProtectionPolicy
from jadawel.core.mcp.models import MCPEndpoint


def create_empty_mcp_protection_policy(
    sender, instance: MCPEndpoint, created: bool, **kwargs
) -> None:
    if created:
        MCPProtectionPolicy.objects.create(endpoint=instance)


def connect_mcp_protection_lifecycle() -> None:
    post_save.connect(
        create_empty_mcp_protection_policy,
        sender=MCPEndpoint,
        dispatch_uid="arabase_create_empty_mcp_protection_policy",
    )
