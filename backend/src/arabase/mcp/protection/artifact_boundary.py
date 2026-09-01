"""Approval boundary for MCP-authored HTML page artifacts.

The page itself is an untrusted template.  This module owns the only transition
that can attach a protected data projection to that template.  It intentionally
stores hashes, stable identities, and content-blind audit metadata; row values
and mask handles never enter an approval record.
"""

from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterable

from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from arabase.mcp.protection.egress import _protected_output_fields
from arabase.mcp.protection.models import (
    ArtifactApproval,
    ArtifactAudience,
    ArtifactAuditEvent,
    ArtifactDraft,
    ArtifactDraftStatus,
    ArtifactManifestField,
    ArtifactProvenance,
    HtmlPageArtifactState,
)
from arabase.mcp.protection.policy_state import (
    get_mcp_protection_policy_state,
)
from arabase.mcp.protection.tokens import MASK_TOKEN_RESERVED_KEY
from arabase.views.constants import MAX_HTML_LENGTH, MAX_ROW_LIMIT
from arabase.views.handler import HtmlPageRevisionHandler
from arabase.views.models import HtmlPageView
from jadawel.contrib.database.fields.models import Field
from jadawel.contrib.database.fields.operations import ReadFieldOperationType
from jadawel.contrib.database.views import signals as view_signals
from jadawel.contrib.database.views.models import (
    ViewFilter,
    ViewFilterGroup,
    ViewGroupBy,
    ViewSort,
)
from jadawel.contrib.database.views.operations import UpdateViewOperationType
from jadawel.core.exceptions import PermissionException
from jadawel.core.handler import CoreHandler
from jadawel.core.mcp.models import MCPEndpoint
from jadawel.core.models import WorkspaceUser

_internal_artifact_update: ContextVar[bool] = ContextVar(
    "mcp_artifact_internal_update", default=False
)


class ArtifactExposureBlocked(APIException):
    """Fixed in-product error used when a protected artifact is not renderable."""

    status_code = 423
    default_code = "MCP_ARTIFACT_UNAVAILABLE"
    default_detail = {
        "code": "MCP_ARTIFACT_UNAVAILABLE",
        "message": "This page is temporarily unavailable until its protected artifact is approved.",
    }


@dataclass(frozen=True, slots=True)
class ArtifactRuntimeAccess:
    """The safe projection a page feed may hand to its sandbox."""

    required: bool
    allowed_protected_field_ids: frozenset[int] = frozenset()
    public_only: bool = False


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def validate_artifact_html(html: str) -> None:
    if not isinstance(html, str):
        raise ValidationError({"html": "HTML must be a string."})
    if len(html.encode("utf-8")) > MAX_HTML_LENGTH:
        raise ValidationError({"html": "The page HTML is too large."})
    # The MCP envelope is deliberately reserved.  A substring check is safer
    # here than trying to parse arbitrary HTML or JavaScript and accidentally
    # accepting a token hidden in a script or attribute.
    if MASK_TOKEN_RESERVED_KEY in html:
        raise ValidationError(
            {"html": "Protected mask tokens cannot be stored in an artifact."}
        )


def _view_configuration(view: HtmlPageView, overrides: dict[str, Any] | None = None):
    """Return a value-free fingerprint input for all render-affecting settings."""

    overrides = overrides or {}
    field_options = [
        {
            "field_id": option.field_id,
            "hidden": option.hidden,
            "order": option.order,
        }
        for option in view.get_field_options(create_if_missing=True)
    ]
    filters = [
        {
            "field_id": item.field_id,
            "type": item.type,
            # Filter values may themselves be sensitive.  They are included only
            # inside this one-way digest input, never persisted as metadata.
            "value_digest": _canonical_digest(item.value),
            "group_id": item.group_id,
        }
        for item in ViewFilter.objects.filter(view_id=view.id).order_by("id")
    ]
    filter_groups = list(
        ViewFilterGroup.objects.filter(view_id=view.id)
        .order_by("id")
        .values("id", "filter_type", "parent_group_id")
    )
    sorts = list(
        ViewSort.objects.filter(view_id=view.id)
        .order_by("id")
        .values("field_id", "order")
    )
    groups = list(
        ViewGroupBy.objects.filter(view_id=view.id)
        .order_by("id")
        .values("field_id", "order")
    )
    values = {
        "view_id": view.id,
        "table_id": view.table_id,
        "field_options": field_options,
        "filter_type": overrides.get("filter_type", view.filter_type),
        "filters_disabled": overrides.get("filters_disabled", view.filters_disabled),
        "filters": filters,
        "filter_groups": filter_groups,
        "sorts": sorts,
        "groups": groups,
        "row_limit": overrides.get("row_limit", view.row_limit),
        "allow_external_resources": overrides.get(
            "allow_external_resources", view.allow_external_resources
        ),
        "public": overrides.get("public", view.public),
        "has_password": bool(
            overrides.get("public_view_password", view.public_view_password)
        ),
        "slug": view.slug,
    }
    return values


def configuration_fingerprint(
    view: HtmlPageView, overrides: dict[str, Any] | None = None
) -> str:
    return _canonical_digest(_view_configuration(view, overrides))


def _audience_fingerprint(view: HtmlPageView, audience: str) -> str:
    if audience == ArtifactAudience.PUBLIC:
        # Do not retain the password hash.  Hashing the current boolean, slug,
        # and view identity makes share rotation/password changes invalidate the
        # approval while keeping the approval record content-blind.
        return _canonical_digest(
            {
                "audience": audience,
                "view_id": view.id,
                "slug": view.slug,
                "public": view.public,
                "has_password": view.public_view_has_password,
            }
        )
    return _canonical_digest(
        {
            "audience": audience,
            "view_id": view.id,
            "workspace_id": view.table.database.workspace_id,
        }
    )


def _policy_for_endpoint(endpoint: MCPEndpoint):
    try:
        return get_mcp_protection_policy_state(endpoint)
    except Exception as exc:
        # Policy-state failures already map to a fixed MCP error.  The artifact
        # boundary uses its own fixed in-product state and must not expose why.
        raise ArtifactExposureBlocked() from exc


def protected_output_for_view(
    view: HtmlPageView, endpoint: MCPEndpoint
) -> tuple[Any, ...]:
    policy = _policy_for_endpoint(endpoint)
    if not policy.has_protected_fields:
        return ()
    direct = tuple(
        field for field in policy.protected_fields if field.table_id == view.table_id
    )
    return _protected_output_fields(
        view.table_id,
        direct,
        policy.protected_fields,
        endpoint.workspace_id,
    )


def view_query_uses_protected_fields(view: HtmlPageView, endpoint: MCPEndpoint) -> bool:
    """Return whether a page's membership/order depends on protected output."""

    if endpoint is None:
        return False
    output_ids = {item.field_id for item in protected_output_for_view(view, endpoint)}
    if not output_ids:
        return False
    return (
        ViewFilter.objects.filter(view_id=view.id, field_id__in=output_ids).exists()
        or ViewSort.objects.filter(view_id=view.id, field_id__in=output_ids).exists()
        or ViewGroupBy.objects.filter(view_id=view.id, field_id__in=output_ids).exists()
    )


def _manifest_fingerprint(
    manifest: Iterable[tuple[int, str]],
) -> str:
    return _canonical_digest(
        [
            {"field_id": field_id, "provenance": provenance}
            for field_id, provenance in sorted(manifest)
        ]
    )


def _manifest_for_draft(draft: ArtifactDraft) -> list[ArtifactManifestField]:
    return list(draft.manifest_fields.order_by("stable_field_id"))


def _audit(
    *,
    event_type: str,
    actor,
    endpoint: MCPEndpoint | None,
    view: HtmlPageView | None,
    draft: ArtifactDraft | None = None,
    approval: ArtifactApproval | None = None,
    audience: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    # Keep this helper deliberately restrictive: callers pass only ids/counts
    # and hashes, never the candidate HTML or row payload.
    ArtifactAuditEvent.objects.create(
        event_type=event_type,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        endpoint=endpoint,
        view=view,
        draft=draft,
        approval=approval,
        audience=audience,
        metadata=metadata or {},
    )


def _ensure_endpoint_owner_can_approve(user, draft: ArtifactDraft) -> None:
    endpoint = draft.endpoint
    view = draft.view
    if not getattr(user, "is_authenticated", False) or user.id != endpoint.user_id:
        raise PermissionDenied("Only the endpoint owner may approve this artifact.")
    if not user.is_active or (
        getattr(user, "profile", None) and user.profile.to_be_deleted
    ):
        raise PermissionDenied("The approver account is not active.")
    if not WorkspaceUser.objects.filter(
        user_id=user.id, workspace_id=endpoint.workspace_id
    ).exists():
        raise PermissionDenied("The approver is not an active workspace member.")
    try:
        CoreHandler().check_permissions(
            user,
            UpdateViewOperationType.type,
            workspace=view.table.database.workspace,
            context=view,
        )
        for manifest in _manifest_for_draft(draft):
            if manifest.field is None:
                raise PermissionDenied("A manifest field is no longer available.")
            CoreHandler().check_permissions(
                user,
                ReadFieldOperationType.type,
                workspace=view.table.database.workspace,
                context=manifest.field,
            )
    except PermissionException as exc:
        raise PermissionDenied(
            "The approver cannot manage this protected page."
        ) from exc


def _validate_manifest_against_view(
    draft: ArtifactDraft, output_fields: tuple[Any, ...]
) -> list[ArtifactManifestField]:
    manifest = _manifest_for_draft(draft)
    expected_ids = list(draft.requested_field_ids)
    actual_ids = [item.stable_field_id for item in manifest]
    if actual_ids != sorted(expected_ids) or len(actual_ids) != len(set(actual_ids)):
        raise ArtifactExposureBlocked()
    output_by_id = {item.field_id: item for item in output_fields}
    pairs = []
    for item in manifest:
        output = output_by_id.get(item.stable_field_id)
        if output is None or item.field is None:
            raise ArtifactExposureBlocked()
        expected_provenance = (
            ArtifactProvenance.DIRECT
            if output.operation_class == "preserve_cell"
            else ArtifactProvenance.DERIVED
        )
        if (
            item.field_id != item.stable_field_id
            or item.table_id_snapshot != item.field.table_id
            or item.field_name_snapshot != item.field.name
            or item.provenance != expected_provenance
        ):
            raise ArtifactExposureBlocked()
        pairs.append((item.stable_field_id, item.provenance))
    if _manifest_fingerprint(pairs) != draft.manifest_fingerprint:
        raise ArtifactExposureBlocked()
    return manifest


def _get_or_create_state(view: HtmlPageView) -> HtmlPageArtifactState:
    state, _ = HtmlPageArtifactState.objects.get_or_create(view=view)
    return state


def _active_approval_for_audience(
    view_id: int, audience: str
) -> ArtifactApproval | None:
    """Return the newest live approval for one audience.

    The state row keeps a pointer to the most recently approved projection for
    compact status responses, but private and public approvals are independent
    authorities.  Looking them up by audience prevents a public approval from
    silently replacing (or expanding) a private one.
    """

    return (
        ArtifactApproval.objects.select_related("draft", "endpoint")
        .filter(view_id=view_id, audience=audience, revoked_at__isnull=True)
        .order_by("-approved_at", "-id")
        .first()
    )


def _safe_update_view(view: HtmlPageView, values: dict[str, Any], user) -> None:
    """Apply a content-blind artifact promotion without the undo HTML payload."""

    if view.html != values.get("html", view.html):
        HtmlPageRevisionHandler().snapshot(view, user)
    for key, value in values.items():
        setattr(view, key, value)
    fields = list(values.keys()) + ["updated_on"]
    token = _internal_artifact_update.set(True)
    try:
        view.save(update_fields=fields)
    finally:
        _internal_artifact_update.reset(token)


@transaction.atomic
def submit_mcp_page_change(
    *,
    user,
    endpoint: MCPEndpoint,
    view: HtmlPageView,
    html: str,
    protected_field_ids: list[int],
    audience: str = ArtifactAudience.AUTHENTICATED,
    pending_view_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Submit a protected draft, or publish a public-only template safely."""

    validate_artifact_html(html)
    pending_view_values = pending_view_values or {}
    allowed_values = {
        key: value
        for key, value in pending_view_values.items()
        if key in {"name", "allow_external_resources", "row_limit"}
    }
    if "row_limit" in allowed_values:
        allowed_values["row_limit"] = max(
            1, min(int(allowed_values["row_limit"]), MAX_ROW_LIMIT)
        )
    if audience not in ArtifactAudience.values:
        raise ValidationError({"audience": "Unsupported artifact audience."})
    if len(protected_field_ids) != len(set(protected_field_ids)):
        raise ValidationError({"protected_field_ids": "Field IDs must be unique."})

    output_fields = protected_output_for_view(view, endpoint)
    if view_query_uses_protected_fields(view, endpoint):
        raise ValidationError(
            {
                "view": (
                    "A page whose filters, sorts, or groups depend on protected "
                    "data cannot expose a protected artifact."
                )
            }
        )
    output_by_id = {item.field_id: item for item in output_fields}
    requested = sorted(protected_field_ids)
    if any(field_id not in output_by_id for field_id in requested):
        raise ValidationError(
            {
                "protected_field_ids": "Every requested field must be a protected output of this page."
            }
        )
    if audience == ArtifactAudience.PUBLIC and not view.public:
        raise ValidationError(
            {"audience": "A public approval requires a publicly shared page."}
        )

    # A page that requests no protected projection is safe to publish directly;
    # the runtime marks it public-only and strips every protected output field.
    if not requested:
        state = _get_or_create_state(view)
        state.endpoint = endpoint
        active_approvals = list(
            ArtifactApproval.objects.select_related("draft").filter(
                view=view, revoked_at__isnull=True
            )
        )
        for old_approval in active_approvals:
            old_approval.revoked_at = timezone.now()
            old_approval.revocation_reason = "public_only_replacement"
            old_approval.save(
                update_fields=["revoked_at", "revocation_reason", "updated_on"]
            )
            old_approval.draft.status = ArtifactDraftStatus.REVOKED
            old_approval.draft.save(update_fields=["status", "updated_on"])
        _safe_update_view(view, {"html": html, **allowed_values}, user)
        state.active_approval = None
        state.public_only = bool(output_fields)
        state.target_generation += 1
        state.save(
            update_fields=[
                "active_approval",
                "endpoint",
                "public_only",
                "target_generation",
                "updated_on",
            ]
        )
        _audit(
            event_type="public_only_published",
            actor=user,
            endpoint=endpoint,
            view=view,
            audience=audience,
            metadata={
                "content_digest": _sha256(html),
                "protected_output_count": len(output_fields),
            },
        )
        return {
            **_page_artifact_summary(view, state),
            "status": "published",
            "protected_field_ids": [],
        }

    policy = _policy_for_endpoint(endpoint)
    manifest_pairs = []
    for field_id in requested:
        output = output_by_id[field_id]
        manifest_pairs.append(
            (
                field_id,
                ArtifactProvenance.DIRECT
                if output.operation_class == "preserve_cell"
                else ArtifactProvenance.DERIVED,
            )
        )

    state = _get_or_create_state(view)
    state.endpoint = endpoint
    ArtifactDraft.objects.filter(
        endpoint=endpoint,
        view=view,
        audience=audience,
        status=ArtifactDraftStatus.PENDING,
    ).update(status=ArtifactDraftStatus.SUPERSEDED)
    draft = ArtifactDraft.objects.create(
        endpoint=endpoint,
        view=view,
        candidate_html=html,
        content_digest=_sha256(html),
        configuration_fingerprint=configuration_fingerprint(view, allowed_values),
        manifest_fingerprint=_manifest_fingerprint(manifest_pairs),
        requested_field_ids=requested,
        pending_view_values=allowed_values,
        audience=audience,
        submitted_by=user if getattr(user, "is_authenticated", False) else None,
    )
    fields = {
        field.id: field
        for field in Field.objects.filter(id__in=requested).select_related("table")
    }
    for field_id, provenance in manifest_pairs:
        field = fields.get(field_id)
        if field is None:
            raise ArtifactExposureBlocked()
        ArtifactManifestField.objects.create(
            draft=draft,
            field=field,
            stable_field_id=field.id,
            field_name_snapshot=field.name,
            table_id_snapshot=field.table_id,
            provenance=provenance,
        )
    state.public_only = False
    state.save(update_fields=["endpoint", "public_only", "updated_on"])
    _audit(
        event_type="draft_submitted",
        actor=user,
        endpoint=endpoint,
        view=view,
        draft=draft,
        audience=audience,
        metadata={
            "content_digest": draft.content_digest,
            "manifest_fingerprint": draft.manifest_fingerprint,
            "protected_field_count": len(requested),
            "policy_revision": policy.revision,
        },
    )
    return {
        **_page_artifact_summary(view, state),
        "status": "pending_approval",
        "draft_id": draft.id,
        "audience": audience,
        "protected_field_ids": requested,
    }


@transaction.atomic
def approve_artifact_draft(*, user, draft_id: int) -> dict[str, Any]:
    draft = (
        ArtifactDraft.objects.select_related(
            "endpoint__workspace", "view__table__database__workspace"
        )
        .select_for_update(of=("self",))
        .get(id=draft_id)
    )
    _ensure_endpoint_owner_can_approve(user, draft)
    if draft.status != ArtifactDraftStatus.PENDING:
        raise ValidationError({"draft_id": "Only a pending draft can be approved."})
    view = HtmlPageView.objects.select_for_update().get(id=draft.view_id)
    state = _get_or_create_state(view)
    output_fields = protected_output_for_view(view, draft.endpoint)
    _validate_manifest_against_view(draft, output_fields)
    if draft.content_digest != _sha256(draft.candidate_html):
        raise ArtifactExposureBlocked()
    if draft.configuration_fingerprint != configuration_fingerprint(
        view, draft.pending_view_values
    ):
        raise ArtifactExposureBlocked()
    policy = _policy_for_endpoint(draft.endpoint)
    if draft.audience == ArtifactAudience.PUBLIC and not view.public:
        raise ArtifactExposureBlocked()
    if draft.audience not in ArtifactAudience.values:
        raise ArtifactExposureBlocked()

    old_approval = _active_approval_for_audience(view.id, draft.audience)
    if old_approval is not None:
        old_approval.revoked_at = timezone.now()
        old_approval.revocation_reason = "superseded"
        old_approval.save(
            update_fields=["revoked_at", "revocation_reason", "updated_on"]
        )
        old_approval.draft.status = ArtifactDraftStatus.SUPERSEDED
        old_approval.draft.save(update_fields=["status", "updated_on"])

    _safe_update_view(
        view,
        {"html": draft.candidate_html, **draft.pending_view_values},
        user,
    )
    state.target_generation += 1
    state.public_only = False
    approval = ArtifactApproval.objects.create(
        draft=draft,
        endpoint=draft.endpoint,
        view=view,
        content_digest=draft.content_digest,
        configuration_fingerprint=draft.configuration_fingerprint,
        manifest_fingerprint=draft.manifest_fingerprint,
        policy_revision=policy.revision,
        access_generation=policy.access_generation,
        target_generation=state.target_generation,
        audience=draft.audience,
        audience_fingerprint=_audience_fingerprint(view, draft.audience),
        approved_by=user,
        approved_at=timezone.now(),
    )
    draft.status = ArtifactDraftStatus.APPROVED
    draft.save(update_fields=["status", "updated_on"])
    state.active_approval = approval
    state.endpoint = draft.endpoint
    state.save(
        update_fields=[
            "active_approval",
            "endpoint",
            "public_only",
            "target_generation",
            "updated_on",
        ]
    )
    _audit(
        event_type="approved",
        actor=user,
        endpoint=draft.endpoint,
        view=view,
        draft=draft,
        approval=approval,
        audience=draft.audience,
        metadata={
            "content_digest": approval.content_digest,
            "manifest_fingerprint": approval.manifest_fingerprint,
            "policy_revision": approval.policy_revision,
            "access_generation": approval.access_generation,
            "target_generation": approval.target_generation,
        },
    )
    return {
        **_page_artifact_summary(view, state),
        "status": "approved",
        "approval_id": approval.id,
        "audience": approval.audience,
        "protected_field_ids": list(draft.requested_field_ids),
    }


@transaction.atomic
def revoke_artifact(
    *, user, view_id: int, reason: str = "manual_revocation"
) -> dict[str, Any]:
    view = (
        HtmlPageView.objects.select_for_update()
        .select_related("table__database")
        .get(id=view_id)
    )
    state = HtmlPageArtifactState.objects.select_for_update().get(view=view)
    endpoint = state.active_approval.endpoint if state.active_approval else None
    if endpoint is None:
        endpoint = (
            ArtifactDraft.objects.filter(view=view)
            .order_by("-created_on", "-id")
            .first()
        )
        endpoint = endpoint.endpoint if endpoint else None
    if endpoint is None or endpoint.user_id != getattr(user, "id", None):
        raise PermissionDenied("Only the artifact endpoint owner may revoke it.")
    approvals = list(
        ArtifactApproval.objects.select_related("draft").filter(
            view=view, revoked_at__isnull=True
        )
    )
    approval = approvals[0] if approvals else None
    now = timezone.now()
    for live_approval in approvals:
        live_approval.revoked_at = now
        live_approval.revocation_reason = reason[:64]
        live_approval.save(
            update_fields=["revoked_at", "revocation_reason", "updated_on"]
        )
        live_approval.draft.status = ArtifactDraftStatus.REVOKED
        live_approval.draft.save(update_fields=["status", "updated_on"])
    if approvals:
        state.active_approval = None
    state.public_only = False
    state.target_generation += 1
    state.save(
        update_fields=[
            "active_approval",
            "public_only",
            "target_generation",
            "updated_on",
        ]
    )
    _audit(
        event_type="revoked",
        actor=user,
        endpoint=endpoint,
        view=view,
        audience=approval.audience if approval is not None else "",
        metadata={"reason": reason[:64], "target_generation": state.target_generation},
    )
    return {**_page_artifact_summary(view, state), "status": "revoked"}


def _page_artifact_summary(
    view: HtmlPageView, state: HtmlPageArtifactState
) -> dict[str, Any]:
    approval = (
        ArtifactApproval.objects.filter(view=view, revoked_at__isnull=True)
        .order_by("-approved_at", "-id")
        .first()
    )
    pending_draft = ArtifactDraft.objects.filter(
        view=view, status=ArtifactDraftStatus.PENDING
    ).first()
    latest_draft = ArtifactDraft.objects.filter(view=view).first()
    if approval and approval.revoked_at is None:
        artifact_state = "approved"
    elif state.public_only:
        artifact_state = "public_only"
    elif pending_draft is not None:
        artifact_state = "pending_approval"
    else:
        artifact_state = "blocked"
    return {
        "view_id": view.id,
        "artifact_state": artifact_state,
        "target_generation": state.target_generation,
        "approval_id": approval.id
        if approval and approval.revoked_at is None
        else None,
        "draft_id": (
            approval.draft_id
            if approval and approval.revoked_at is None
            else pending_draft.id
            if pending_draft is not None
            else None
        ),
        "audience": (
            approval.audience
            if approval and approval.revoked_at is None
            else pending_draft.audience
            if pending_draft is not None
            else None
        ),
        "endpoint_id": (
            approval.endpoint_id
            if approval and approval.revoked_at is None
            else latest_draft.endpoint_id
            if latest_draft is not None
            else state.endpoint_id
        ),
        "protected_field_ids": list(
            (
                approval.draft.requested_field_ids
                if approval and approval.revoked_at is None
                else pending_draft.requested_field_ids
                if pending_draft is not None
                else latest_draft.requested_field_ids
                if latest_draft is not None
                else []
            )
        ),
    }


def _validated_active_approval(
    *, view: HtmlPageView, state: HtmlPageArtifactState, audience: str, user=None
) -> ArtifactRuntimeAccess:
    approval = _active_approval_for_audience(view.id, audience)
    if approval is None and state.public_only:
        if (
            state.active_approval is not None
            and state.active_approval.revoked_at is None
        ):
            raise ArtifactExposureBlocked()
        return ArtifactRuntimeAccess(required=True, public_only=True)
    if state.public_only:
        return ArtifactRuntimeAccess(required=True, public_only=True)
    if approval is None or approval.revoked_at is not None:
        raise ArtifactExposureBlocked()
    if approval.audience != audience:
        raise ArtifactExposureBlocked()
    if audience == ArtifactAudience.PUBLIC and not view.public:
        raise ArtifactExposureBlocked()
    if audience == ArtifactAudience.AUTHENTICATED and user is not None:
        try:
            allowed = CoreHandler().check_permissions(
                user,
                UpdateViewOperationType.type,
                workspace=view.table.database.workspace,
                context=view,
                raise_permission_exceptions=False,
            )
        except TypeError:
            # Older core permission managers do not expose the optional flag;
            # the outer view endpoint has already performed read permission.
            allowed = True
        if allowed is not True:
            raise ArtifactExposureBlocked()
    # ``target_generation`` is a view-level status counter.  It can advance
    # when an independent audience (private/public) is approved, so it is not
    # itself an authority check for this audience.  Content/configuration,
    # policy generations, and the audience fingerprint below are the exact
    # bindings; explicit replacement/revocation marks the old approval dead.
    if approval.content_digest != _sha256(view.html):
        raise ArtifactExposureBlocked()
    if approval.configuration_fingerprint != configuration_fingerprint(view):
        raise ArtifactExposureBlocked()
    if approval.audience_fingerprint != _audience_fingerprint(view, audience):
        raise ArtifactExposureBlocked()
    try:
        policy = get_mcp_protection_policy_state(approval.endpoint)
    except Exception as exc:
        raise ArtifactExposureBlocked() from exc
    if (
        policy.revision != approval.policy_revision
        or policy.access_generation != approval.access_generation
        or approval.endpoint.workspace_id != view.table.database.workspace_id
    ):
        raise ArtifactExposureBlocked()
    output_fields = protected_output_for_view(view, approval.endpoint)
    manifest = _validate_manifest_against_view(approval.draft, output_fields)
    return ArtifactRuntimeAccess(
        required=True,
        allowed_protected_field_ids=frozenset(
            item.stable_field_id for item in manifest
        ),
    )


def page_runtime_access(
    view: HtmlPageView,
    *,
    audience: str = ArtifactAudience.AUTHENTICATED,
    user=None,
) -> ArtifactRuntimeAccess:
    """Validate the durable binding before a page document or row feed is read."""

    state = (
        HtmlPageArtifactState.objects.select_related(
            "endpoint", "active_approval__draft__endpoint"
        )
        .filter(view=view)
        .first()
    )
    if state is None:
        return ArtifactRuntimeAccess(required=False)
    approval = _active_approval_for_audience(view.id, audience)
    endpoint = approval.endpoint if approval is not None else state.endpoint
    if endpoint is None:
        latest_draft = (
            ArtifactDraft.objects.filter(view=view)
            .order_by("-created_on", "-id")
            .first()
        )
        endpoint = latest_draft.endpoint if latest_draft else state.endpoint
    if endpoint is None:
        raise ArtifactExposureBlocked()
    output_fields = protected_output_for_view(view, endpoint)
    if not output_fields:
        return ArtifactRuntimeAccess(required=False)
    if view_query_uses_protected_fields(view, endpoint):
        raise ArtifactExposureBlocked()
    return _validated_active_approval(
        view=view, state=state, audience=audience, user=user
    )


def page_feed_field_ids(
    view: HtmlPageView,
    *,
    audience: str = ArtifactAudience.AUTHENTICATED,
    user=None,
) -> set[int] | None:
    """Return the allowed field projection, or ``None`` for the legacy path."""

    access = page_runtime_access(view, audience=audience, user=user)
    if not access.required:
        return None
    state = HtmlPageArtifactState.objects.filter(view=view).first()
    if state is None:
        return None
    approval = _active_approval_for_audience(view.id, audience)
    latest_draft = (
        ArtifactDraft.objects.filter(view=view).order_by("-created_on", "-id").first()
    )
    endpoint = (
        approval.endpoint
        if approval
        else latest_draft.endpoint
        if latest_draft
        else state.endpoint
    )
    if endpoint is None:
        raise ArtifactExposureBlocked()
    output_ids = {item.field_id for item in protected_output_for_view(view, endpoint)}
    # The view type supplies the authoritative active field options.
    from arabase.views.view_types import HtmlPageViewType

    visible_ids = set(
        HtmlPageViewType()
        .get_visible_field_options_in_order(view)
        .values_list("field_id", flat=True)
    )
    return (visible_ids - output_ids) | set(access.allowed_protected_field_ids)


def artifact_status_for_view(view: HtmlPageView) -> dict[str, Any]:
    state = HtmlPageArtifactState.objects.filter(view=view).first()
    if state is None:
        return {"artifact_state": "unmanaged"}
    summary = _page_artifact_summary(view, state)
    approval = state.active_approval
    if approval is not None and approval.revoked_at is None:
        try:
            _validated_active_approval(
                view=view, state=state, audience=approval.audience
            )
        except ArtifactExposureBlocked:
            summary.update(
                {
                    "artifact_state": "blocked",
                    "approval_id": None,
                }
            )
    return summary


def human_page_update_as_artifact(
    *, user, view: HtmlPageView, values: dict[str, Any]
) -> dict[str, Any] | None:
    """Route a direct REST source edit through the same draft boundary as MCP."""

    if "html" not in values:
        return None
    state = HtmlPageArtifactState.objects.filter(view=view).first()
    if state is None:
        return None
    approval = state.active_approval
    latest_draft = ArtifactDraft.objects.filter(view=view).first()
    endpoint = (
        approval.endpoint
        if approval and approval.revoked_at is None
        else latest_draft.endpoint
        if latest_draft is not None
        else state.endpoint
    )
    if endpoint is None:
        return None
    output_fields = protected_output_for_view(view, endpoint)
    if not output_fields:
        return None
    draft = approval.draft if approval and approval.revoked_at is None else latest_draft
    protected_field_ids = list(draft.requested_field_ids) if draft else []
    audience = (
        approval.audience
        if approval and approval.revoked_at is None
        else draft.audience
        if draft
        else ArtifactAudience.AUTHENTICATED
    )
    return submit_mcp_page_change(
        user=user,
        endpoint=endpoint,
        view=view,
        html=values["html"],
        protected_field_ids=protected_field_ids,
        audience=audience,
        pending_view_values={
            key: value for key, value in values.items() if key != "html"
        },
    )


@transaction.atomic
def invalidate_artifact_for_view(
    view: HtmlPageView, *, actor=None, reason: str
) -> None:
    """Revoke a projection when an ordinary page edit changes its binding."""

    if _internal_artifact_update.get():
        return
    state = (
        HtmlPageArtifactState.objects.select_for_update()
        .select_related("active_approval__endpoint")
        .filter(view_id=view.id)
        .first()
    )
    if state is None:
        return
    approvals = list(
        ArtifactApproval.objects.select_related("draft", "endpoint").filter(
            view_id=view.id, revoked_at__isnull=True
        )
    )
    approval = approvals[0] if approvals else None
    now = timezone.now()
    for approval in approvals:
        approval.revoked_at = now
        approval.revocation_reason = reason[:64]
        approval.save(update_fields=["revoked_at", "revocation_reason", "updated_on"])
        approval.draft.status = ArtifactDraftStatus.REVOKED
        approval.draft.save(update_fields=["status", "updated_on"])
    state.active_approval = None
    state.public_only = False
    state.target_generation += 1
    state.save(
        update_fields=[
            "active_approval",
            "public_only",
            "target_generation",
            "updated_on",
        ]
    )
    endpoint = approvals[0].endpoint if approvals else None
    _audit(
        event_type="invalidated",
        actor=actor,
        endpoint=endpoint,
        view=view,
        approval=approval,
        audience=approvals[0].audience if approvals else "",
        metadata={"reason": reason[:64], "target_generation": state.target_generation},
    )


def connect_artifact_lifecycle() -> None:
    """Subscribe to every view-setting signal that can stale an approval."""

    def updated(sender, view, user=None, **kwargs):
        if isinstance(view, HtmlPageView):
            invalidate_artifact_for_view(view, actor=user, reason="view_updated")

    def child_changed(
        sender, view_filter=None, view_sort=None, view=None, user=None, **kwargs
    ):
        target = view
        if target is None and view_filter is not None:
            target = view_filter.view
        if target is None and view_sort is not None:
            target = view_sort.view
        if isinstance(target, HtmlPageView):
            invalidate_artifact_for_view(
                target, actor=user, reason="view_configuration_changed"
            )

    def options_changed(sender, view, user=None, **kwargs):
        if isinstance(view, HtmlPageView):
            invalidate_artifact_for_view(
                view, actor=user, reason="field_projection_changed"
            )

    view_signals.view_updated.connect(
        updated, dispatch_uid="arabase_mcp_artifact_view_updated"
    )
    for signal in (
        view_signals.view_filter_created,
        view_signals.view_filter_updated,
        view_signals.view_filter_deleted,
        view_signals.view_sort_created,
        view_signals.view_sort_updated,
        view_signals.view_sort_deleted,
    ):
        signal.connect(child_changed, dispatch_uid=f"arabase_mcp_artifact_{id(signal)}")
    view_signals.view_field_options_updated.connect(
        options_changed, dispatch_uid="arabase_mcp_artifact_field_options"
    )
