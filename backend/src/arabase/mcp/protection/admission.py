from django.conf import settings

from rest_framework.exceptions import ValidationError

MCP_PROTECTION_STAFF_FLAG = "mcp-protected-fields-staff"
MCP_PROTECTION_FLAG = "mcp-protected-fields"


def ensure_policy_admission_allowed(user) -> None:
    """Gate policy admission without ever weakening enforcement."""

    configured_flags = settings.FEATURE_FLAGS
    if isinstance(configured_flags, str):
        configured_flags = (configured_flags,)
    flags = {str(flag).strip().lower() for flag in configured_flags}
    if "*" in flags or MCP_PROTECTION_FLAG in flags:
        return
    if MCP_PROTECTION_STAFF_FLAG in flags and user.is_staff:
        return
    raise ValidationError(
        {
            "protected_field_ids": (
                "MCP protected-field policies are not enabled for this account."
            )
        }
    )
