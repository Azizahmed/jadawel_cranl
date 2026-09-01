from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

import pytest

from arabase.mcp.protection.models import MCPProtectionPolicy
from jadawel.core.mcp.models import MCPEndpoint


@pytest.mark.django_db
def test_protection_check_strict_passes_for_a_consistent_empty_policy(data_fixture):
    data_fixture.create_mcp_endpoint()
    output = StringIO()

    call_command("mcp_protection_check", "--strict", stdout=output)

    assert output.getvalue().strip() == "MCP protection check passed"


@pytest.mark.django_db
def test_protection_check_strict_reports_a_missing_policy_without_secrets(
    data_fixture,
):
    endpoint = data_fixture.create_mcp_endpoint()
    MCPProtectionPolicy.objects.filter(endpoint=endpoint).delete()
    output = StringIO()

    with pytest.raises(CommandError, match="POLICY_COUNT_MISMATCH") as exc_info:
        call_command("mcp_protection_check", "--strict", stdout=output)

    assert endpoint.key not in str(exc_info.value)
    assert "MCP protection check failed: POLICY_COUNT_MISMATCH" in str(exc_info.value)


@pytest.mark.django_db
@override_settings(FEATURE_FLAGS=[])
def test_protection_check_does_not_require_vault_for_empty_policies(data_fixture):
    data_fixture.create_mcp_endpoint()
    output = StringIO()

    call_command("mcp_protection_check", "--strict", stdout=output)

    assert MCPEndpoint.objects.count() == 1
    assert output.getvalue().strip() == "MCP protection check passed"
