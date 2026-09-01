from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_delete, post_save, pre_save

from rest_framework.exceptions import PermissionDenied

from arabase.mcp.protection.models import (
    MCPProtectedField,
    MCPProtectedFieldState,
    MCPProtectionLifecycleAudit,
    MCPProtectionLifecycleStatus,
    MCPProtectionPolicy,
    MCPProtectionSafeReason,
)
from jadawel.contrib.database.fields.models import Field
from jadawel.contrib.database.models import Database
from jadawel.contrib.database.table.models import Table
from jadawel.core.mcp.exceptions import MCPEndpointDoesNotExist
from jadawel.core.mcp.models import MCPEndpoint
from jadawel.core.models import (
    WORKSPACE_USER_PERMISSION_ADMIN,
    UserProfile,
    Workspace,
    WorkspaceUser,
)


def create_empty_mcp_protection_policy(
    sender, instance: MCPEndpoint, created: bool, **kwargs
) -> None:
    if created:
        MCPProtectionPolicy.objects.create(endpoint=instance)


def record_mcp_protection_lifecycle_transition(
    *,
    policy: MCPProtectionPolicy,
    from_lifecycle_status: str,
    to_lifecycle_status: str,
    reason_code: str = "",
    event_type: str = "lifecycle_transition",
    actor=None,
    metadata: dict | None = None,
) -> None:
    """Write a content-blind lifecycle transition audit entry."""

    if from_lifecycle_status == to_lifecycle_status and not reason_code:
        return
    MCPProtectionLifecycleAudit.objects.create(
        endpoint_id=policy.endpoint_id,
        actor=actor,
        event_type=event_type,
        from_lifecycle_status=from_lifecycle_status,
        to_lifecycle_status=to_lifecycle_status,
        reason_code=reason_code,
        policy_revision=policy.revision,
        access_generation=policy.access_generation,
        metadata=metadata or {},
    )


@transaction.atomic
def delete_ownerless_suspended_endpoint(*, user, endpoint_id: int) -> None:
    """Let a workspace admin remove only an endpoint with no viable owner.

    The owner-only core MCP delete path remains unchanged.  This additive path is
    intentionally narrower: an admin must be an active workspace administrator,
    the endpoint must be suspended or protection-blocked, and the original owner
    must no longer be an active workspace member/account.  The audit is written
    before deletion and survives through its nullable endpoint foreign key.
    """

    try:
        endpoint = (
            MCPEndpoint.objects.select_for_update(of=("self",))
            .select_related("workspace", "user__profile", "arabase_protection_policy")
            .get(id=endpoint_id)
        )
    except MCPEndpoint.DoesNotExist as exc:
        raise MCPEndpointDoesNotExist from exc

    if not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied(
            "Only an active workspace administrator may delete this endpoint."
        )
    if (
        endpoint.workspace.trashed
        or not WorkspaceUser.objects.filter(
            user_id=user.id,
            workspace_id=endpoint.workspace_id,
            permissions=WORKSPACE_USER_PERMISSION_ADMIN,
        ).exists()
    ):
        raise PermissionDenied(
            "Only a workspace administrator may delete this endpoint."
        )

    policy = endpoint.arabase_protection_policy
    if policy.lifecycle_status not in (
        MCPProtectionLifecycleStatus.SUSPENDED,
        MCPProtectionLifecycleStatus.PROTECTION_BLOCKED,
    ):
        raise PermissionDenied(
            "Only a suspended or blocked ownerless endpoint may be deleted."
        )

    owner_active_member = (
        endpoint.user is not None
        and endpoint.user.is_active
        and not getattr(getattr(endpoint.user, "profile", None), "to_be_deleted", False)
        and WorkspaceUser.objects.filter(
            user_id=endpoint.user_id,
            workspace_id=endpoint.workspace_id,
        ).exists()
    )
    if owner_active_member:
        raise PermissionDenied(
            "The endpoint owner must be inactive or absent from the workspace."
        )

    MCPProtectionLifecycleAudit.objects.create(
        endpoint=endpoint,
        actor=user,
        event_type="ownerless_admin_delete",
        from_lifecycle_status=policy.lifecycle_status,
        to_lifecycle_status="deleted",
        reason_code=policy.safe_reason_code,
        policy_revision=policy.revision,
        access_generation=policy.access_generation,
        metadata={"endpoint_id": endpoint.id},
    )
    endpoint.delete()


def _bump_policies(endpoint_ids, *, reason=None, lifecycle_status=None):
    endpoint_ids = list(set(endpoint_ids))
    before = {
        row["endpoint_id"]: row
        for row in MCPProtectionPolicy.objects.filter(
            endpoint_id__in=endpoint_ids
        ).values(
            "endpoint_id",
            "revision",
            "access_generation",
            "lifecycle_status",
            "safe_reason_code",
        )
    }
    updates = {
        "revision": F("revision") + 1,
        "access_generation": F("access_generation") + 1,
    }
    if reason is not None:
        updates["safe_reason_code"] = reason
    if lifecycle_status is not None:
        updates["lifecycle_status"] = lifecycle_status
    MCPProtectionPolicy.objects.filter(endpoint_id__in=endpoint_ids).update(**updates)
    if reason is None and lifecycle_status is None:
        return
    target_status = lifecycle_status
    target_reason = reason
    audits = []
    for row in before.values():
        if row["lifecycle_status"] == (
            target_status or row["lifecycle_status"]
        ) and row["safe_reason_code"] == (target_reason or row["safe_reason_code"]):
            continue
        audits.append(
            MCPProtectionLifecycleAudit(
                endpoint_id=row["endpoint_id"],
                event_type="lifecycle_transition",
                from_lifecycle_status=row["lifecycle_status"],
                to_lifecycle_status=target_status or row["lifecycle_status"],
                reason_code=target_reason or row["safe_reason_code"],
                policy_revision=row["revision"] + 1,
                access_generation=row["access_generation"] + 1,
                metadata={},
            )
        )
    if audits:
        MCPProtectionLifecycleAudit.objects.bulk_create(audits)


def _suspend_workspace_policies(workspace_id: int, suspended: bool) -> None:
    endpoint_ids = MCPEndpoint.objects.filter(workspace_id=workspace_id).values_list(
        "id", flat=True
    )
    if suspended:
        _bump_policies(
            endpoint_ids,
            reason=MCPProtectionSafeReason.WORKSPACE_SUSPENDED,
            lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
        )
    else:
        policies = list(
            MCPProtectionPolicy.objects.filter(
                endpoint_id__in=endpoint_ids,
                lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
                safe_reason_code=MCPProtectionSafeReason.WORKSPACE_SUSPENDED,
            )
        )
        MCPProtectionPolicy.objects.filter(
            id__in=[policy.id for policy in policies]
        ).update(
            revision=F("revision") + 1,
            access_generation=F("access_generation") + 1,
            lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
            safe_reason_code=MCPProtectionSafeReason.NONE,
        )
        for policy in policies:
            policy.revision += 1
            policy.access_generation += 1
            record_mcp_protection_lifecycle_transition(
                policy=policy,
                from_lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
                to_lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
                reason_code=MCPProtectionSafeReason.NONE,
                metadata={"trigger": "workspace_restored"},
            )


def _set_hierarchy_protection_state(
    *, table_ids=None, database_ids=None, trashed: bool
):
    relation_filter = {}
    if table_ids is not None:
        relation_filter["field__table_id__in"] = table_ids
    if database_ids is not None:
        relation_filter["field__table__database_id__in"] = database_ids
    relations = MCPProtectedField.objects.filter(**relation_filter)
    if not relations.exists():
        return
    endpoint_ids = list(
        relations.values_list("policy__endpoint_id", flat=True).distinct()
    )
    if trashed:
        relations.filter(state=MCPProtectedFieldState.ACTIVE).update(
            state=MCPProtectedFieldState.SUSPENDED,
            safe_reason_code=MCPProtectionSafeReason.POLICY_RELATION_INVALID,
        )
        _bump_policies(
            endpoint_ids,
            reason=MCPProtectionSafeReason.POLICY_RELATION_INVALID,
            lifecycle_status=MCPProtectionLifecycleStatus.PROTECTION_BLOCKED,
        )
        return

    # A parent can be restored before all of its children. Keep the policy
    # blocked until every stable field identity is usable again.
    relations.filter(
        state=MCPProtectedFieldState.SUSPENDED,
        safe_reason_code=MCPProtectionSafeReason.POLICY_RELATION_INVALID,
        field__trashed=False,
        field__table__trashed=False,
        field__table__database__trashed=False,
    ).update(
        state=MCPProtectedFieldState.ACTIVE,
        safe_reason_code=MCPProtectionSafeReason.NONE,
    )
    _bump_policies(endpoint_ids)
    for policy in MCPProtectionPolicy.objects.filter(endpoint_id__in=endpoint_ids):
        if policy.protected_fields.filter(
            state=MCPProtectedFieldState.SUSPENDED
        ).exists():
            continue
        previous_status = policy.lifecycle_status
        policy.lifecycle_status = MCPProtectionLifecycleStatus.ACTIVE
        policy.safe_reason_code = MCPProtectionSafeReason.NONE
        policy.save(
            update_fields=["lifecycle_status", "safe_reason_code", "updated_on"]
        )
        record_mcp_protection_lifecycle_transition(
            policy=policy,
            from_lifecycle_status=previous_status,
            to_lifecycle_status=policy.lifecycle_status,
            reason_code=MCPProtectionSafeReason.NONE,
            metadata={"trigger": "hierarchy_restored"},
        )


def _capture_field_state(sender, instance: Field, **kwargs):
    if not isinstance(instance, Field):
        return
    if not instance.pk:
        instance._mcp_protection_previous_state = None
        return
    instance._mcp_protection_previous_state = (
        Field.objects_and_trash.filter(pk=instance.pk)
        .values("content_type_id", "trashed")
        .first()
    )


def _field_changed(sender, instance: Field, created: bool, **kwargs):
    if not isinstance(instance, Field):
        return
    previous = getattr(instance, "_mcp_protection_previous_state", None)
    changed_type = (
        previous is not None and previous["content_type_id"] != instance.content_type_id
    )
    changed_trash = previous is not None and previous["trashed"] != instance.trashed
    if not created and not changed_type and not changed_trash:
        return
    relations = MCPProtectedField.objects.filter(field_id=instance.id)
    if not relations.exists():
        return
    hierarchy_trashed = (
        instance.trashed or instance.table.trashed or instance.table.database.trashed
    )
    if hierarchy_trashed:
        active_relations = relations.filter(state=MCPProtectedFieldState.ACTIVE)
        active_relations.update(
            state=MCPProtectedFieldState.SUSPENDED,
            safe_reason_code=MCPProtectionSafeReason.POLICY_RELATION_INVALID,
        )
        _bump_policies(
            relations.values_list("policy__endpoint_id", flat=True),
            reason=MCPProtectionSafeReason.POLICY_RELATION_INVALID,
            lifecycle_status=MCPProtectionLifecycleStatus.PROTECTION_BLOCKED,
        )
    elif changed_type or changed_trash:
        if changed_trash and not (
            instance.trashed
            or instance.table.trashed
            or instance.table.database.trashed
        ):
            relations.filter(
                state=MCPProtectedFieldState.SUSPENDED,
                safe_reason_code=MCPProtectionSafeReason.POLICY_RELATION_INVALID,
            ).update(
                state=MCPProtectedFieldState.ACTIVE,
                safe_reason_code=MCPProtectionSafeReason.NONE,
            )
        endpoint_ids = list(
            relations.values_list("policy__endpoint_id", flat=True).distinct()
        )
        _bump_policies(endpoint_ids)
        if changed_trash and not instance.trashed:
            for policy in MCPProtectionPolicy.objects.filter(
                endpoint_id__in=endpoint_ids
            ):
                if not policy.protected_fields.filter(
                    state=MCPProtectedFieldState.SUSPENDED
                ).exists():
                    previous_status = policy.lifecycle_status
                    policy.lifecycle_status = MCPProtectionLifecycleStatus.ACTIVE
                    policy.safe_reason_code = MCPProtectionSafeReason.NONE
                    policy.save(
                        update_fields=[
                            "lifecycle_status",
                            "safe_reason_code",
                            "updated_on",
                        ]
                    )
                    record_mcp_protection_lifecycle_transition(
                        policy=policy,
                        from_lifecycle_status=previous_status,
                        to_lifecycle_status=policy.lifecycle_status,
                        reason_code=MCPProtectionSafeReason.NONE,
                        metadata={"trigger": "hierarchy_restored"},
                    )


def _workspace_changed(sender, instance: Workspace, created: bool, **kwargs):
    previous = getattr(instance, "_mcp_protection_previous_trash_state", None)
    if not created and previous is not None and previous != instance.trashed:
        _suspend_workspace_policies(instance.id, instance.trashed)


def _capture_workspace_state(sender, instance: Workspace, **kwargs):
    if not instance.pk:
        instance._mcp_protection_previous_trash_state = None
        return
    instance._mcp_protection_previous_trash_state = (
        Workspace.objects_and_trash.filter(pk=instance.pk)
        .values_list("trashed", flat=True)
        .first()
    )


def _capture_hierarchy_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._mcp_protection_previous_trash_state = None
        return
    instance._mcp_protection_previous_trash_state = (
        sender.objects_and_trash.filter(pk=instance.pk)
        .values_list("trashed", flat=True)
        .first()
    )


def _table_changed(sender, instance: Table, created: bool, **kwargs):
    previous = getattr(instance, "_mcp_protection_previous_trash_state", None)
    if not created and previous is not None and previous != instance.trashed:
        _set_hierarchy_protection_state(
            table_ids=[instance.id], trashed=instance.trashed
        )


def _database_changed(sender, instance: Database, created: bool, **kwargs):
    previous = getattr(instance, "_mcp_protection_previous_trash_state", None)
    if not created and previous is not None and previous != instance.trashed:
        _set_hierarchy_protection_state(
            database_ids=[instance.id], trashed=instance.trashed
        )


def _workspace_user_changed(sender, instance: WorkspaceUser, **kwargs):
    endpoint_ids = MCPEndpoint.objects.filter(
        user_id=instance.user_id, workspace_id=instance.workspace_id
    ).values_list("id", flat=True)
    if not WorkspaceUser.objects.filter(
        user_id=instance.user_id, workspace_id=instance.workspace_id
    ).exists():
        _bump_policies(
            endpoint_ids,
            reason=MCPProtectionSafeReason.MEMBERSHIP_CHANGED,
            lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
        )
    else:
        _bump_policies(endpoint_ids)


def _workspace_user_deleted(sender, instance: WorkspaceUser, **kwargs):
    _workspace_user_changed(sender, instance)


def _user_changed(sender, instance, **kwargs):
    previous = getattr(instance, "_mcp_protection_previous_active_state", None)
    if previous is not None and previous == instance.is_active:
        return
    endpoint_ids = MCPEndpoint.objects.filter(user_id=instance.id).values_list(
        "id", flat=True
    )
    if not instance.is_active:
        _bump_policies(
            endpoint_ids,
            reason=MCPProtectionSafeReason.USER_INACTIVE,
            lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
        )
        return
    policies = list(
        MCPProtectionPolicy.objects.filter(
            endpoint_id__in=endpoint_ids,
            lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
            safe_reason_code=MCPProtectionSafeReason.USER_INACTIVE,
        )
    )
    MCPProtectionPolicy.objects.filter(
        id__in=[policy.id for policy in policies]
    ).update(
        revision=F("revision") + 1,
        access_generation=F("access_generation") + 1,
        lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
        safe_reason_code=MCPProtectionSafeReason.NONE,
    )
    for policy in policies:
        policy.revision += 1
        policy.access_generation += 1
        record_mcp_protection_lifecycle_transition(
            policy=policy,
            from_lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
            to_lifecycle_status=MCPProtectionLifecycleStatus.ACTIVE,
            reason_code=MCPProtectionSafeReason.NONE,
            metadata={"trigger": "user_reactivated"},
        )


def _user_profile_changed(sender, instance: UserProfile, **kwargs):
    endpoint_ids = MCPEndpoint.objects.filter(user_id=instance.user_id).values_list(
        "id", flat=True
    )
    if instance.to_be_deleted:
        _bump_policies(
            endpoint_ids,
            reason=MCPProtectionSafeReason.USER_INACTIVE,
            lifecycle_status=MCPProtectionLifecycleStatus.SUSPENDED,
        )


def _capture_user_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._mcp_protection_previous_active_state = None
        return
    instance._mcp_protection_previous_active_state = (
        sender.objects.filter(pk=instance.pk)
        .values_list("is_active", flat=True)
        .first()
    )


def _capture_endpoint_state(sender, instance: MCPEndpoint, **kwargs):
    if not instance.pk:
        instance._mcp_protection_previous_key = None
        return
    instance._mcp_protection_previous_key = (
        MCPEndpoint.objects_and_trash.filter(pk=instance.pk)
        .values_list("key", flat=True)
        .first()
    )


def _endpoint_changed(sender, instance: MCPEndpoint, created: bool, **kwargs):
    previous_key = getattr(instance, "_mcp_protection_previous_key", None)
    if not created and previous_key is not None and previous_key != instance.key:
        policy = MCPProtectionPolicy.objects.filter(endpoint_id=instance.id).first()
        if (
            policy is not None
            and policy.lifecycle_status != MCPProtectionLifecycleStatus.ACTIVE
        ):
            _bump_policies([instance.id])
            return
        _bump_policies(
            [instance.id],
            reason=MCPProtectionSafeReason.CREDENTIAL_ROTATED,
            lifecycle_status=MCPProtectionLifecycleStatus.PROTECTION_BLOCKED,
        )


def connect_mcp_protection_lifecycle() -> None:
    post_save.connect(
        create_empty_mcp_protection_policy,
        sender=MCPEndpoint,
        dispatch_uid="arabase_create_empty_mcp_protection_policy",
    )
    pre_save.connect(
        _capture_field_state,
        sender=None,
        dispatch_uid="arabase_capture_mcp_protection_field_state",
    )
    post_save.connect(
        _field_changed,
        sender=None,
        dispatch_uid="arabase_mcp_protection_field_changed",
    )
    pre_save.connect(
        _capture_workspace_state,
        sender=Workspace,
        dispatch_uid="arabase_capture_mcp_protection_workspace_state",
    )
    post_save.connect(
        _workspace_changed,
        sender=Workspace,
        dispatch_uid="arabase_mcp_protection_workspace_changed",
    )
    pre_save.connect(
        _capture_hierarchy_state,
        sender=Table,
        dispatch_uid="arabase_capture_mcp_protection_table_state",
    )
    post_save.connect(
        _table_changed,
        sender=Table,
        dispatch_uid="arabase_mcp_protection_table_changed",
    )
    pre_save.connect(
        _capture_hierarchy_state,
        sender=Database,
        dispatch_uid="arabase_capture_mcp_protection_database_state",
    )
    post_save.connect(
        _database_changed,
        sender=Database,
        dispatch_uid="arabase_mcp_protection_database_changed",
    )
    post_save.connect(
        _workspace_user_changed,
        sender=WorkspaceUser,
        dispatch_uid="arabase_mcp_protection_workspace_user_changed",
    )
    post_delete.connect(
        _workspace_user_deleted,
        sender=WorkspaceUser,
        dispatch_uid="arabase_mcp_protection_workspace_user_deleted",
    )
    post_save.connect(
        _user_changed,
        sender=get_user_model(),
        dispatch_uid="arabase_mcp_protection_user_changed",
    )
    pre_save.connect(
        _capture_user_state,
        sender=get_user_model(),
        dispatch_uid="arabase_capture_mcp_protection_user_state",
    )
    post_save.connect(
        _user_profile_changed,
        sender=UserProfile,
        dispatch_uid="arabase_mcp_protection_user_profile_changed",
    )
    pre_save.connect(
        _capture_endpoint_state,
        sender=MCPEndpoint,
        dispatch_uid="arabase_capture_mcp_protection_endpoint_state",
    )
    post_save.connect(
        _endpoint_changed,
        sender=MCPEndpoint,
        dispatch_uid="arabase_mcp_protection_endpoint_changed",
    )
