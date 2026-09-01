import base64
import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from django.conf import settings

from redis import Redis
from redis.exceptions import RedisError

from arabase.mcp.protection.canonical import (
    CANONICAL_VALUE_VERSION,
    canonicalize_typed_value,
)
from arabase.mcp.protection.tokens import GeneratedMaskToken, generate_mask_token

MASK_TOKEN_TTL_SECONDS = 24 * 60 * 60
MASK_TOKEN_REDIS_PREFIX = "jadawel:mcp-protection:v1:"
MASK_TOKEN_EXPIRY_INDEX = f"{MASK_TOKEN_REDIS_PREFIX}expiry"
MASK_TOKEN_ENDPOINT_INDEX_PREFIX = f"{MASK_TOKEN_REDIS_PREFIX}endpoint:"
MAX_ISSUANCE_MEMORY_RATIO = 0.60
MAX_ENDPOINT_TOKENS = 10_000
MAX_GLOBAL_TOKENS = 50_000

_ISSUE_TOKEN_SCRIPT = """
local now = tonumber(redis.call('TIME')[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
  return -1
end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3]) then
  return -1
end
local stored = redis.call('SET', KEYS[3], ARGV[4], 'NX', 'EX', ARGV[1])
if not stored then
  return 0
end
redis.call('ZADD', KEYS[1], ARGV[5], ARGV[6])
redis.call('ZADD', KEYS[2], ARGV[5], ARGV[6])
return 1
"""


class MaskTokenVaultUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MaskTokenBinding:
    endpoint_id: int
    workspace_id: int
    table_id: int
    row_id: int
    field_id: int
    policy_revision: int
    access_generation: int
    operation_class: str
    observed_row_state: str
    field_type: str


@dataclass(frozen=True, slots=True)
class IssuedMaskToken:
    raw_handle: str
    digest: str
    envelope: dict


def _load_active_fingerprint_key() -> tuple[str, bytes]:
    key_id = settings.MCP_PROTECTION_ACTIVE_KEY_ID
    encoded_key = settings.MCP_PROTECTION_FINGERPRINT_KEYS.get(key_id)
    if not encoded_key:
        raise MaskTokenVaultUnavailable
    try:
        key = base64.b64decode(encoded_key, validate=True)
    except (ValueError, TypeError) as exc:
        raise MaskTokenVaultUnavailable from exc
    if len(key) != 32:
        raise MaskTokenVaultUnavailable
    return key_id, key


def _load_fingerprint_key(key_id: str) -> bytes:
    encoded_key = settings.MCP_PROTECTION_FINGERPRINT_KEYS.get(key_id)
    if not encoded_key:
        raise MaskTokenVaultUnavailable
    try:
        key = base64.b64decode(encoded_key, validate=True)
    except (ValueError, TypeError) as exc:
        raise MaskTokenVaultUnavailable from exc
    if len(key) != 32:
        raise MaskTokenVaultUnavailable
    return key


class RedisMaskTokenVault:
    """Digest-addressed Redis vault which never persists the token or value."""

    def __init__(self, redis_client: Redis | None = None):
        self._enforce_memory_headroom = redis_client is None
        if redis_client is not None:
            self.redis = redis_client
            return
        redis_url = settings.MCP_PROTECTION_REDIS_URL
        if not redis_url and settings.MCP_PROTECTION_ALLOW_SHARED_REDIS:
            redis_url = settings.REDIS_URL
        if not redis_url:
            raise MaskTokenVaultUnavailable
        try:
            self.redis = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=0.25,
                socket_timeout=0.5,
            )
        except (TypeError, ValueError) as exc:
            raise MaskTokenVaultUnavailable from exc

    def issue(self, binding: MaskTokenBinding, value: Any) -> IssuedMaskToken:
        self._ensure_issuance_headroom()
        key_id, fingerprint_key = _load_active_fingerprint_key()
        canonical_value = canonicalize_typed_value(binding.field_type, value)
        fingerprint = hmac.new(
            fingerprint_key, canonical_value, hashlib.sha256
        ).hexdigest()
        token = generate_mask_token()
        expires_at = datetime.now(UTC) + timedelta(seconds=MASK_TOKEN_TTL_SECONDS)
        record = {
            **asdict(binding),
            "canonicalization_version": CANONICAL_VALUE_VERSION,
            "expires_at": expires_at.isoformat(),
            "fingerprint_key_id": key_id,
            "value_fingerprint": fingerprint,
        }
        try:
            result = self.redis.register_script(_ISSUE_TOKEN_SCRIPT)(
                keys=[
                    MASK_TOKEN_EXPIRY_INDEX,
                    f"{MASK_TOKEN_ENDPOINT_INDEX_PREFIX}{binding.endpoint_id}",
                    f"{MASK_TOKEN_REDIS_PREFIX}{token.digest}",
                ],
                args=[
                    MASK_TOKEN_TTL_SECONDS,
                    MAX_GLOBAL_TOKENS,
                    MAX_ENDPOINT_TOKENS,
                    json.dumps(record, separators=(",", ":"), sort_keys=True),
                    # Keep the reservation at least as long as the Redis TTL;
                    # flooring a fractional Unix timestamp could release it early.
                    int(expires_at.timestamp()) + 1,
                    token.digest,
                ],
            )
        except RedisError as exc:
            raise MaskTokenVaultUnavailable from exc
        if result != 1:
            raise MaskTokenVaultUnavailable
        return _issued(token)

    def _ensure_issuance_headroom(self) -> None:
        """Stop new issuance before the dedicated vault reaches its safety floor.

        Test fakes and explicitly injected Redis clients are deliberately exempt:
        production clients are always constructed from the configured URL and
        therefore get the bounded configuration check on every issuance batch.
        """

        if not self._enforce_memory_headroom:
            return
        try:
            config_get = getattr(self.redis, "config_get", None)
            if config_get is None:
                raise RedisError("Redis configuration cannot be verified")
            memory = config_get("maxmemory")
            policy = config_get("maxmemory-policy")
            maxmemory = int(memory.get("maxmemory", 0))
            if maxmemory <= 0 or policy.get("maxmemory-policy") != "noeviction":
                raise RedisError("Redis is not a bounded noeviction vault")
            used_memory = int(self.redis.info("memory").get("used_memory", 0))
            if used_memory / maxmemory >= MAX_ISSUANCE_MEMORY_RATIO:
                raise RedisError("Redis memory headroom is below the safety floor")
        except (RedisError, OSError, ValueError, TypeError, AttributeError) as exc:
            raise MaskTokenVaultUnavailable from exc

    def redeem(
        self, raw_handle: str, binding: MaskTokenBinding, current_value: Any
    ) -> bool:
        """Validate a same-cell token against its current row state.

        A successful redemption is intentionally non-consuming: retries of an
        idempotent MCP request must preserve the same cell while the token remains
        valid.  Redis contains only the binding and a keyed fingerprint, never the
        raw value or handle.
        """

        try:
            digest = hashlib.sha256(raw_handle.encode("ascii")).hexdigest()
            stored = self.redis.get(f"{MASK_TOKEN_REDIS_PREFIX}{digest}")
        except (AttributeError, TypeError, UnicodeEncodeError):
            return False
        except RedisError as exc:
            raise MaskTokenVaultUnavailable from exc
        if not stored:
            return False
        try:
            record = json.loads(stored)
            expires_at = datetime.fromisoformat(record["expires_at"])
            if expires_at <= datetime.now(UTC):
                return False
            expected = asdict(binding)
            if any(record.get(key) != value for key, value in expected.items()):
                return False
            if record.get("canonicalization_version") != CANONICAL_VALUE_VERSION:
                return False
            fingerprint_key = _load_fingerprint_key(record["fingerprint_key_id"])
            canonical_value = canonicalize_typed_value(
                binding.field_type, current_value
            )
            fingerprint = hmac.new(
                fingerprint_key, canonical_value, hashlib.sha256
            ).hexdigest()
        except (
            KeyError,
            AttributeError,
            TypeError,
            ValueError,
            OverflowError,
            UnicodeEncodeError,
            MaskTokenVaultUnavailable,
        ):
            return False
        return hmac.compare_digest(record.get("value_fingerprint", ""), fingerprint)

    def delete(self, digests: list[str]) -> None:
        if not digests:
            return
        for digest in digests:
            key = f"{MASK_TOKEN_REDIS_PREFIX}{digest}"
            try:
                record = self.redis.get(key)
            except RedisError:
                # An uncertain cleanup keeps the sorted-set reservation until TTL.
                continue
            endpoint_id = None
            try:
                endpoint_id = json.loads(record)["endpoint_id"] if record else None
            except (KeyError, TypeError, ValueError):
                pass
            try:
                deleted = self.redis.delete(key)
                if deleted:
                    self.redis.zrem(MASK_TOKEN_EXPIRY_INDEX, digest)
                    if endpoint_id is not None:
                        self.redis.zrem(
                            f"{MASK_TOKEN_ENDPOINT_INDEX_PREFIX}{endpoint_id}",
                            digest,
                        )
            except RedisError:
                # An uncertain cleanup keeps the sorted-set reservation until TTL.
                pass


def _issued(token: GeneratedMaskToken) -> IssuedMaskToken:
    return IssuedMaskToken(
        raw_handle=token.raw_handle,
        digest=token.digest,
        envelope=token.envelope,
    )


def get_mask_token_vault() -> RedisMaskTokenVault:
    return RedisMaskTokenVault()
