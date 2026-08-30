from django.urls import reverse

import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_202_ACCEPTED

from arabase.mcp.page import services
from arabase.mcp.protection.artifact_boundary import (
    ArtifactExposureBlocked,
    approve_artifact_draft,
    page_feed_field_ids,
    page_runtime_access,
    submit_mcp_page_change,
    validate_artifact_html,
)
from arabase.mcp.protection.models import (
    ArtifactApproval,
    ArtifactAudience,
    ArtifactAuditEvent,
    ArtifactDraft,
    ArtifactDraftStatus,
    ArtifactProvenance,
    MCPProtectedField,
)
from arabase.views.view_types import HtmlPageViewType
from jadawel.contrib.database.views.handler import ViewHandler

PAGE_V1 = "<!doctype html><body><h1>v1</h1></body>"
PAGE_V2 = "<!doctype html><body><h1>v2</h1></body>"


@pytest.fixture
def protected_page(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    secret = data_fixture.create_text_field(table=table, name="Secret", primary=True)
    visible = data_fixture.create_text_field(table=table, name="Visible")
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=secret
    )
    view = ViewHandler().create_view(
        user, table, HtmlPageViewType.type, name="Report", html=PAGE_V1
    )
    return user, workspace, table, secret, visible, endpoint, view


@pytest.mark.django_db
def test_mcp_page_update_stays_pending_until_human_approval(protected_page):
    user, workspace, _table, secret, _visible, endpoint, view = protected_page

    result = services.update_page_view(
        user,
        workspace,
        view.id,
        html=PAGE_V2,
        endpoint=endpoint,
        protected_field_ids=[secret.id],
    )

    view.refresh_from_db()
    draft = ArtifactDraft.objects.get(id=result["draft_id"])
    assert result["status"] == "pending_approval"
    assert result["artifact_state"] == "pending_approval"
    assert view.html == PAGE_V1
    assert draft.status == ArtifactDraftStatus.PENDING
    assert draft.candidate_html == PAGE_V2
    manifest = draft.manifest_fields.get()
    assert manifest.stable_field_id == secret.id
    assert manifest.provenance == ArtifactProvenance.DIRECT
    assert "Secret" not in ArtifactAuditEvent.objects.last().metadata

    approved = approve_artifact_draft(user=user, draft_id=draft.id)

    view.refresh_from_db()
    assert approved["status"] == "approved"
    assert view.html == PAGE_V2
    assert ArtifactApproval.objects.get(draft=draft).approved_by_id == user.id
    access = page_runtime_access(view, user=user)
    assert access.allowed_protected_field_ids == {secret.id}


@pytest.mark.django_db
def test_approval_is_invalidated_when_view_configuration_changes(protected_page):
    user, workspace, _table, secret, _visible, endpoint, view = protected_page
    pending = services.update_page_view(
        user,
        workspace,
        view.id,
        html=PAGE_V2,
        endpoint=endpoint,
        protected_field_ids=[secret.id],
    )
    approve_artifact_draft(user=user, draft_id=pending["draft_id"])

    ViewHandler().update_view(user, view, name="Renamed")

    with pytest.raises(ArtifactExposureBlocked):
        page_runtime_access(view, user=user)


@pytest.mark.django_db
def test_public_and_authenticated_approvals_are_separate(protected_page):
    user, workspace, _table, secret, _visible, endpoint, view = protected_page
    ViewHandler().update_view(user, view, public=True)

    pending = services.update_page_view(
        user,
        workspace,
        view.id,
        html=PAGE_V2,
        endpoint=endpoint,
        protected_field_ids=[secret.id],
        audience=ArtifactAudience.PUBLIC,
    )
    approve_artifact_draft(user=user, draft_id=pending["draft_id"])
    view.refresh_from_db()

    assert page_runtime_access(view, audience=ArtifactAudience.PUBLIC).required
    with pytest.raises(ArtifactExposureBlocked):
        page_runtime_access(view, user=user)


@pytest.mark.django_db
def test_public_only_artifact_removes_protected_projection(protected_page):
    user, workspace, _table, secret, visible, endpoint, view = protected_page

    result = services.update_page_view(
        user,
        workspace,
        view.id,
        html=PAGE_V2,
        endpoint=endpoint,
        protected_field_ids=[],
    )

    assert result["status"] == "published"
    allowed = page_feed_field_ids(view, user=user)
    assert secret.id not in allowed
    assert visible.id in allowed


@pytest.mark.django_db
def test_protected_query_dependency_is_rejected(protected_page):
    user, workspace, _table, secret, _visible, endpoint, view = protected_page
    ViewHandler().create_filter(user, view, secret, "equal", "sensitive")

    with pytest.raises(ValidationError):
        submit_mcp_page_change(
            user=user,
            endpoint=endpoint,
            view=view,
            html=PAGE_V2,
            protected_field_ids=[secret.id],
        )


@pytest.mark.django_db
def test_artifact_review_api_exposes_only_safe_state(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    secret = data_fixture.create_text_field(table=table, name="Secret", primary=True)
    endpoint = data_fixture.create_mcp_endpoint(user=user, workspace=workspace)
    MCPProtectedField.objects.create(
        policy=endpoint.arabase_protection_policy, field=secret
    )
    view = ViewHandler().create_view(
        user, table, HtmlPageViewType.type, name="Report", html=PAGE_V1
    )
    headers = {"HTTP_AUTHORIZATION": f"JWT {token}"}

    draft_response = api_client.post(
        reverse("api:arabase:mcp_artifact_draft"),
        {
            "endpoint_id": endpoint.id,
            "view_id": view.id,
            "html": PAGE_V2,
            "protected_field_ids": [secret.id],
        },
        format="json",
        **headers,
    )
    assert draft_response.status_code == HTTP_201_CREATED
    draft_body = draft_response.json()
    assert "candidate_html" not in draft_body
    assert "Secret" not in str(draft_body)

    state_response = api_client.get(
        reverse("api:arabase:mcp_artifact_state", kwargs={"view_id": view.id}),
        **headers,
    )
    assert state_response.status_code == HTTP_200_OK
    assert state_response.json()["artifact_state"] == "pending_approval"


@pytest.mark.django_db
def test_direct_view_patch_routes_html_to_a_new_draft(api_client, protected_page):
    user, workspace, _table, secret, _visible, endpoint, view = protected_page
    initial = services.update_page_view(
        user,
        workspace,
        view.id,
        html=PAGE_V2,
        endpoint=endpoint,
        protected_field_ids=[secret.id],
    )
    approve_artifact_draft(user=user, draft_id=initial["draft_id"])
    view.refresh_from_db()
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse("api:database:views:item", kwargs={"view_id": view.id}),
        {"html": "<!doctype html><body>v3</body>"},
        format="json",
    )

    assert response.status_code == HTTP_202_ACCEPTED
    assert response.json()["status"] == "pending_approval"
    view.refresh_from_db()
    assert view.html == PAGE_V2


def test_artifact_html_never_accepts_a_mask_envelope():
    with pytest.raises(ValidationError):
        validate_artifact_html('<div data="$jadawelProtected">secret</div>')
