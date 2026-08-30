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


class RedisMaskTokenVault:
    """Digest-addressed Redis vault which never persists the token or value."""

    def __init__(self, redis_client: Redis | None = None):
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
            stored = self.redis.set(
                f"{MASK_TOKEN_REDIS_PREFIX}{token.digest}",
                json.dumps(record, separators=(",", ":"), sort_keys=True),
                ex=MASK_TOKEN_TTL_SECONDS,
                nx=True,
            )
        except RedisError as exc:
            raise MaskTokenVaultUnavailable from exc
        if not stored:
            raise MaskTokenVaultUnavailable
        return _issued(token)

    def delete(self, digests: list[str]) -> None:
        if not digests:
            return
        try:
            self.redis.delete(
                *(f"{MASK_TOKEN_REDIS_PREFIX}{digest}" for digest in digests)
            )
        except RedisError:
            pass


def _issued(token: GeneratedMaskToken) -> IssuedMaskToken:
    return IssuedMaskToken(
        raw_handle=token.raw_handle,
        digest=token.digest,
        envelope=token.envelope,
    )


def get_mask_token_vault() -> RedisMaskTokenVault:
    return RedisMaskTokenVault()
