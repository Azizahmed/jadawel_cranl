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
