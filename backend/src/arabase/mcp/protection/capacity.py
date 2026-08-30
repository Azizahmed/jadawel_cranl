"""Distributed admission control for protected MCP token issuance."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Iterator

from redis.exceptions import RedisError

from arabase.mcp.protection.vault import (
    MASK_TOKEN_REDIS_PREFIX,
    MaskTokenVaultUnavailable,
    RedisMaskTokenVault,
)

MAX_ACTIVE_ISSUERS_PER_ENDPOINT = 2
MAX_ACTIVE_ISSUERS_GLOBAL = 6
ISSUER_LEASE_SECONDS = 2
ISSUER_WAIT_SECONDS = 0.25
ISSUER_INDEX = f"{MASK_TOKEN_REDIS_PREFIX}issuers"
ISSUER_ENDPOINT_INDEX_PREFIX = f"{MASK_TOKEN_REDIS_PREFIX}issuers:endpoint:"

_ACQUIRE_SCRIPT = """
local now = tonumber(redis.call('TIME')[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
  return 0
end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3]) then
  return 0
end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
redis.call('ZADD', KEYS[2], ARGV[1], ARGV[4])
return 1
"""


@contextmanager
def issuance_lease(
    endpoint_id: int,
    vault: RedisMaskTokenVault,
) -> Iterator[None]:
    """Admit at most two endpoint and six deployment-wide issuers."""

    member = uuid.uuid4().hex
    endpoint_key = f"{ISSUER_ENDPOINT_INDEX_PREFIX}{endpoint_id}"
    deadline = time.monotonic() + ISSUER_WAIT_SECONDS
    acquired = False
    try:
        while time.monotonic() <= deadline:
            try:
                expires_at = int(time.time()) + ISSUER_LEASE_SECONDS
                acquired = (
                    vault.redis.register_script(_ACQUIRE_SCRIPT)(
                        keys=[ISSUER_INDEX, endpoint_key],
                        args=[
                            expires_at,
                            MAX_ACTIVE_ISSUERS_PER_ENDPOINT,
                            MAX_ACTIVE_ISSUERS_GLOBAL,
                            member,
                        ],
                    )
                    == 1
                )
            except RedisError as exc:
                raise MaskTokenVaultUnavailable from exc
            if acquired:
                break
            time.sleep(0.01)
        if not acquired:
            raise MaskTokenVaultUnavailable
        yield
    finally:
        if acquired:
            try:
                vault.redis.zrem(ISSUER_INDEX, member)
                vault.redis.zrem(endpoint_key, member)
            except RedisError:
                # The short lease expires on its own. Never turn a successful
                # protected response into a plaintext fallback because cleanup
                # was uncertain.
                pass
