import base64
import hashlib
import secrets
from dataclasses import dataclass

MASK_TOKEN_RESERVED_KEY = "$jadawelProtected"
MASK_TOKEN_VERSION = 1
MASK_TOKEN_HANDLE_BYTES = 32


@dataclass(frozen=True, slots=True)
class GeneratedMaskToken:
    raw_handle: str
    digest: str

    @property
    def envelope(self) -> dict:
        return {
            MASK_TOKEN_RESERVED_KEY: {
                "v": MASK_TOKEN_VERSION,
                "token": self.raw_handle,
            }
        }


def generate_mask_token() -> GeneratedMaskToken:
    raw_bytes = secrets.token_bytes(MASK_TOKEN_HANDLE_BYTES)
    raw_handle = base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")
    return GeneratedMaskToken(
        raw_handle=raw_handle,
        digest=hashlib.sha256(raw_handle.encode("ascii")).hexdigest(),
    )
