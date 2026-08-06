"""Accept the legacy ``BASEROW_*`` environment variable names.

Settings read ``JADAWEL_*``. Existing deployments still set the old
``BASEROW_*`` names in their dashboards and compose files, so every legacy
name is copied to its new spelling before the first setting is read. The new
name always wins; the legacy name is only consulted when the new one is
absent.

Renaming an environment variable without this shim is silently destructive.
``BASEROW_JWT_SIGNING_KEY`` is the clearest example: when it goes missing the
signing key falls back to ``SECRET_KEY``, which invalidates every issued JWT
and logs out every user with nothing written to the log.

Remove this module only after every deployment sets ``JADAWEL_*``.
"""

import os

LEGACY_PREFIX = "BASEROW_"
PREFIX = "JADAWEL_"


def apply(environ: dict[str, str] | None = None) -> list[str]:
    """Copy every ``BASEROW_*`` name to ``JADAWEL_*`` when the latter is unset.

    Returns the legacy names that were used, so callers can warn about them.
    """

    environ = os.environ if environ is None else environ
    used = []
    for legacy, value in list(environ.items()):
        if not legacy.startswith(LEGACY_PREFIX):
            continue
        current = PREFIX + legacy[len(LEGACY_PREFIX) :]
        if current not in environ:
            environ[current] = value
            used.append(legacy)
    return sorted(used)
