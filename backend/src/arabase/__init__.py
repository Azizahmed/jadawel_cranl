"""Arabase — the Jadawel (جداول) fork's own backend code.

All Arabic-first and enterprise-equivalent functionality that we add on top of the
Baserow MIT core lives under this package, kept separate from ``baserow.*`` so that
quarterly ``upstream`` merges stay cheap. Nothing proprietary from Baserow's
``premium``/``enterprise`` plugins may ever be copied in here (see PATCHES.md).

Planned sub-apps (created as their phase begins):

* ``arabase.fields``   — Hijri date field type            (Phase 2)
* ``arabase.search``   — Arabic search normalization + ICU (Phase 2)
* ``arabase.sso``      — OIDC / auth-provider interface     (Phase 3)
* ``arabase.audit``    — append-only audit log             (Phase 3)
* ``arabase.rbac``     — role-based access control         (Phase 3)
"""

default_app_config = "arabase.apps.ArabaseConfig"
