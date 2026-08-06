"""Arabase — the Jadawel (جداول) fork's own backend code.

All Arabic-first and enterprise-equivalent functionality that we add on top of the
upstream-derived core lives under this package, kept separate from ``jadawel.*`` so
that provenance stays legible: ``jadawel.*`` is inherited, ``arabase.*`` is ours.
Nothing proprietary from Jadawel's ``premium``/``enterprise`` plugins may ever be
copied in here (see PATCHES.md).

Planned sub-apps (created as their phase begins):

* ``arabase.fields``   — Hijri date field type            (Phase 2)
* ``arabase.search``   — Arabic search normalization + ICU (Phase 2)
* ``arabase.sso``      — OIDC / auth-provider interface     (Phase 3)
* ``arabase.audit``    — append-only audit log             (Phase 3)
* ``arabase.rbac``     — role-based access control         (Phase 3)
"""

default_app_config = "arabase.apps.ArabaseConfig"
