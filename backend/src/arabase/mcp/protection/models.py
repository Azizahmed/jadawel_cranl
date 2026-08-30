from django.conf import settings
from django.db import models

from jadawel.contrib.database.fields.models import Field
from jadawel.core.mcp.models import MCPEndpoint
from jadawel.core.mixins import CreatedAndUpdatedOnMixin


class MCPProtectionLifecycleStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    PROTECTION_BLOCKED = "protection_blocked", "Protection blocked"


class MCPProtectedFieldState(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class MCPProtectionSafeReason(models.TextChoices):
    NONE = "", "None"
    POLICY_COUNT_MISMATCH = "POLICY_COUNT_MISMATCH", "Policy count mismatch"
    POLICY_STATE_INVALID = "POLICY_STATE_INVALID", "Policy state invalid"
    POLICY_RELATION_INVALID = "POLICY_RELATION_INVALID", "Policy relation invalid"
    WORKSPACE_SUSPENDED = "WORKSPACE_SUSPENDED", "Workspace suspended"
    MEMBERSHIP_CHANGED = "MEMBERSHIP_CHANGED", "Membership changed"
    USER_INACTIVE = "USER_INACTIVE", "User inactive"
    CREDENTIAL_ROTATED = "CREDENTIAL_ROTATED", "Credential rotated"
    PROTECTION_REDIS_UNAVAILABLE = (
        "PROTECTION_REDIS_UNAVAILABLE",
        "Protection Redis unavailable",
    )


class MCPProtectionPolicy(CreatedAndUpdatedOnMixin, models.Model):
    """The explicit, revisioned protection state for one MCP endpoint."""

    endpoint = models.OneToOneField(
        MCPEndpoint,
        on_delete=models.CASCADE,
        related_name="arabase_protection_policy",
    )
    revision = models.PositiveBigIntegerField(default=1)
    access_generation = models.PositiveBigIntegerField(default=1)
    lifecycle_status = models.CharField(
        max_length=32,
        choices=MCPProtectionLifecycleStatus.choices,
        default=MCPProtectionLifecycleStatus.ACTIVE,
    )
    safe_reason_code = models.CharField(
        max_length=64,
        choices=MCPProtectionSafeReason.choices,
        blank=True,
        default=MCPProtectionSafeReason.NONE,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(revision__gte=1),
                name="arabase_mcp_policy_revision_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(access_generation__gte=1),
                name="arabase_mcp_access_generation_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
                        safe_reason_code=MCPProtectionSafeReason.NONE,
                    )
                    | (
                        ~models.Q(lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE)
                        & ~models.Q(safe_reason_code=MCPProtectionSafeReason.NONE)
                    )
                ),
                name="arabase_mcp_policy_status_reason_consistent",
            ),
        ]


class MCPProtectedField(CreatedAndUpdatedOnMixin, models.Model):
    """A protected stable field identity belonging to an endpoint policy."""

    policy = models.ForeignKey(
        MCPProtectionPolicy,
        on_delete=models.CASCADE,
        related_name="protected_fields",
    )
    field = models.ForeignKey(
        Field,
        on_delete=models.PROTECT,
        related_name="mcp_protection_relations",
    )
    state = models.CharField(
        max_length=16,
        choices=MCPProtectedFieldState.choices,
        default=MCPProtectedFieldState.ACTIVE,
    )
    safe_reason_code = models.CharField(
        max_length=64,
        choices=MCPProtectionSafeReason.choices,
        blank=True,
        default=MCPProtectionSafeReason.NONE,
    )

    class Meta:
        ordering = ("field_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("policy", "field"),
                name="arabase_unique_mcp_policy_field",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        state=MCPProtectedFieldState.ACTIVE,
                        safe_reason_code=MCPProtectionSafeReason.NONE,
                    )
                    | (
                        models.Q(state=MCPProtectedFieldState.SUSPENDED)
                        & ~models.Q(safe_reason_code=MCPProtectionSafeReason.NONE)
                    )
                ),
                name="arabase_mcp_field_state_reason_consistent",
            ),
        ]
        indexes = [
            models.Index(
                fields=("field", "state"),
                name="ara_mcp_pf_field_state_idx",
            ),
            models.Index(
                fields=("policy", "state"),
                name="ara_mcp_pf_policy_state_idx",
            ),
        ]


class MCPProtectionCommand(CreatedAndUpdatedOnMixin, models.Model):
    """Bounded idempotency state for one composite endpoint creation command."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mcp_protection_commands",
    )
    idempotency_key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    endpoint = models.OneToOneField(
        MCPEndpoint,
        on_delete=models.CASCADE,
        related_name="arabase_creation_command",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("actor", "idempotency_key"),
                name="arabase_unique_mcp_command_key",
            )
        ]
        indexes = [
            models.Index(
                fields=("actor", "created_on"),
                name="ara_mcp_cmd_actor_created_idx",
            )
        ]


class MCPProtectionEditCommand(CreatedAndUpdatedOnMixin, models.Model):
    """Bounded idempotency state for one endpoint policy replacement."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mcp_protection_edit_commands",
    )
    policy = models.ForeignKey(
        MCPProtectionPolicy,
        on_delete=models.CASCADE,
        related_name="edit_commands",
    )
    idempotency_key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    resulting_revision = models.PositiveBigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("actor", "idempotency_key"),
                name="arabase_unique_mcp_edit_command_key",
            )
        ]
        indexes = [
            models.Index(
                fields=("actor", "created_on"),
                name="ara_mcp_edit_actor_created_idx",
            )
        ]


class MCPProtectionMutationAudit(CreatedAndUpdatedOnMixin, models.Model):
    """Content-blind audit record for a protected MCP row mutation."""

    endpoint = models.ForeignKey(
        MCPEndpoint,
        on_delete=models.SET_NULL,
        null=True,
        related_name="protection_mutation_audits",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="mcp_protection_mutation_audits",
    )
    tool_type = models.CharField(max_length=64)
    table_id = models.PositiveBigIntegerField()
    row_count = models.PositiveIntegerField()
    outcome = models.CharField(max_length=24, default="success")
    policy_revision = models.PositiveBigIntegerField(default=0)
    access_generation = models.PositiveBigIntegerField(default=0)
    protected_field_ids = models.JSONField(default=list)

    class Meta:
        indexes = [
            models.Index(
                fields=("endpoint", "created_on"),
                name="ara_mcp_audit_ep_created_idx",
            )
        ]
