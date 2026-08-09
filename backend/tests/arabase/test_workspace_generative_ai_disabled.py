"""The workspace-level generative AI settings endpoint is removed in Jadawel.

Provider credentials are an instance concern (env vars) or an integration concern
(``AIIntegration.ai_settings``); letting every workspace admin store third-party
API keys on the workspace is not a shape we want to expose. The frontend tab is
unregistered in ``web-frontend/modules/arabase/registryPlugin.js`` and the route
is gone from ``jadawel/api/workspaces/urls.py`` (logged in ``PATCHES.md``); this
test keeps the API half from creeping back in.
"""

from django.urls import NoReverseMatch, reverse

import pytest
from rest_framework.status import HTTP_404_NOT_FOUND


def test_generative_ai_settings_route_is_not_registered():
    with pytest.raises(NoReverseMatch):
        reverse("api:workspaces:generative_ai_settings", kwargs={"workspace_id": 1})


@pytest.mark.django_db
def test_generative_ai_settings_url_is_not_served(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)

    for method in (api_client.get, api_client.patch):
        response = method(
            f"/api/workspaces/{workspace.id}/settings/generative-ai/",
            format="json",
            **{"HTTP_AUTHORIZATION": f"JWT {token}"},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
