"""Fork-hygiene guardrails.

These tests fail loudly if the proprietary Baserow premium/enterprise code ever
leaks back into the build (e.g. via an upstream merge), and confirm our additive
``arabase`` app is wired in. Keep them fast and DB-free.
"""

import importlib

from django.conf import settings

import pytest


def test_arabase_app_is_installed():
    assert "arabase" in settings.INSTALLED_APPS


def test_oss_only_and_no_builtin_plugins():
    assert settings.BASEROW_OSS_ONLY is True
    assert settings.BASEROW_BUILT_IN_PLUGINS == []


@pytest.mark.parametrize("module_name", ["baserow_premium", "baserow_enterprise"])
def test_proprietary_plugins_are_not_importable(module_name):
    # The premium/ and enterprise/ directories are deleted; importing them must fail.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


@pytest.mark.parametrize("app_label", ["baserow_premium", "baserow_enterprise"])
def test_proprietary_apps_not_in_installed_apps(app_label):
    assert app_label not in settings.INSTALLED_APPS
