"""Fork-hygiene guardrails.

These tests fail loudly if Baserow's proprietary premium/enterprise code ever leaks
back into the build (e.g. via an upstream merge), confirm our additive ``arabase``
app is wired in, and hold the attribution the MIT and Apache licences require.
Keep them fast and DB-free.
"""

import importlib
from pathlib import Path

from django.conf import settings

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Renaming the fork must never rewrite an upstream author's name. MIT terminates the
# grant if the notice is dropped, and Apache-2.0 section 4 requires notices be kept.
# Two separate rename passes have flipped one of these to "Jadawel B.V." already, so
# they are asserted rather than trusted.
REQUIRED_ATTRIBUTION = [
    ("LICENSE", "Copyright (c) 2019-present Baserow B.V."),
    ("deploy/helm/jadawel/values.yaml", "Copyright Baserow B.V. All Rights Reserved."),
    (
        "backend/src/jadawel/contrib/database/fields/dependencies/"
        "circular_reference_checker.py",
        "Copyright 2020, Jack Linke",
    ),
    (
        "backend/src/jadawel/contrib/database/fields/dependencies/"
        "circular_reference_checker.py",
        "Copyright (c) 2019-present Baserow B.V.",
    ),
    ("formula/JadawelFormulaLexer.g4", "Copyright 2018 Tal Shprecher"),
]


def test_arabase_app_is_installed():
    assert "arabase" in settings.INSTALLED_APPS


def test_oss_only_and_no_builtin_plugins():
    assert settings.JADAWEL_OSS_ONLY is True
    assert settings.JADAWEL_BUILT_IN_PLUGINS == []


@pytest.mark.parametrize("module_name", ["baserow_premium", "baserow_enterprise"])
def test_proprietary_plugins_are_not_importable(module_name):
    # The premium/ and enterprise/ directories are deleted; importing them must fail.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


@pytest.mark.parametrize("app_label", ["baserow_premium", "baserow_enterprise"])
def test_proprietary_apps_not_in_installed_apps(app_label):
    assert app_label not in settings.INSTALLED_APPS


@pytest.mark.parametrize("relative_path,notice", REQUIRED_ATTRIBUTION)
def test_upstream_attribution_is_intact(relative_path, notice):
    path = REPO_ROOT / relative_path
    assert path.is_file(), f"{relative_path} is missing"
    assert notice in path.read_text(encoding="utf-8"), (
        f"{relative_path} no longer carries {notice!r}. A rename pass must never "
        f"rewrite an upstream author's name — restore it."
    )
