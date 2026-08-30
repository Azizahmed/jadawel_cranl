import fakeredis
import pytest

import arabase.mcp.protection.capacity as capacity
from arabase.mcp.protection.vault import MaskTokenVaultUnavailable, RedisMaskTokenVault


def test_issuance_lease_enforces_endpoint_cap_and_releases(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    vault = RedisMaskTokenVault(redis_client=redis)
    monkeypatch.setattr(capacity, "ISSUER_WAIT_SECONDS", 0.05)
    monkeypatch.setattr(capacity, "MAX_ACTIVE_ISSUERS_PER_ENDPOINT", 1)

    first = capacity.issuance_lease(endpoint_id=7, vault=vault)
    first.__enter__()
    try:
        with pytest.raises(MaskTokenVaultUnavailable):
            with capacity.issuance_lease(endpoint_id=7, vault=vault):
                pass
    finally:
        first.__exit__(None, None, None)

    with capacity.issuance_lease(endpoint_id=7, vault=vault):
        assert redis.zcard(capacity.ISSUER_INDEX) == 1

    assert redis.zcard(capacity.ISSUER_INDEX) == 0
