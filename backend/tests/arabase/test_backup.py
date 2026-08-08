from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from arabase.backup.config import BackupConfig
from arabase.backup.runner import BackupError, _dump_argv, _prune, run_backup


def _config(**overrides):
    defaults = dict(
        enabled=True,
        bucket="jadawel-backups",
        prefix="postgres/",
        endpoint_url=None,
        region="me-south-1",
        access_key_id="key",
        secret_access_key="secret",
        retention_days=14,
        crontab="0 23 * * *",
        sse=None,
    )
    defaults.update(overrides)
    return BackupConfig(**defaults)


class TestConfig:
    def test_reads_the_environment(self, monkeypatch):
        monkeypatch.setenv("JADAWEL_BACKUP_ENABLED", "true")
        monkeypatch.setenv("JADAWEL_BACKUP_S3_BUCKET", "bucket")
        monkeypatch.setenv("JADAWEL_BACKUP_RETENTION_DAYS", "30")

        config = BackupConfig.from_env()

        assert config.enabled is True
        assert config.bucket == "bucket"
        assert config.retention_days == 30

    def test_is_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("JADAWEL_BACKUP_ENABLED", raising=False)

        assert BackupConfig.from_env().enabled is False

    def test_normalises_a_prefix_without_a_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("JADAWEL_BACKUP_S3_PREFIX", "dumps")

        assert BackupConfig.from_env().prefix == "dumps/"

    def test_falls_back_when_retention_is_not_a_number(self, monkeypatch):
        monkeypatch.setenv("JADAWEL_BACKUP_RETENTION_DAYS", "soon")

        assert BackupConfig.from_env().retention_days == 14

    def test_reports_every_missing_credential(self):
        errors = _config(bucket="", access_key_id=None).validation_errors()

        assert len(errors) == 2

    def test_refuses_the_public_media_bucket_without_a_prefix(self, monkeypatch):
        monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "shared")

        errors = _config(bucket="shared", prefix="").validation_errors()

        assert any("public-read" in error for error in errors)

    def test_allows_the_media_bucket_under_its_own_prefix(self, monkeypatch):
        monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "shared")

        assert _config(bucket="shared", prefix="postgres/").validation_errors() == []


@patch("arabase.backup.runner._pg_dump_path", return_value="/usr/bin/pg_dump")
class TestDumpArgv:
    def test_never_puts_the_password_in_argv(self, _path):
        argv = _dump_argv(
            {
                "NAME": "jadawel",
                "USER": "jadawel",
                "PASSWORD": "hunter2",
                "HOST": "db",
                "PORT": "5432",
            }
        )

        assert "hunter2" not in " ".join(argv)
        assert "--username=jadawel" in argv
        assert argv[-1] == "jadawel"

    def test_uses_an_absolute_executable_path(self, _path):
        argv = _dump_argv({"NAME": "jadawel", "USER": "", "HOST": "", "PORT": ""})

        assert argv[0] == "/usr/bin/pg_dump"

    def test_omits_host_and_port_when_absent(self, _path):
        argv = _dump_argv({"NAME": "jadawel", "USER": "", "HOST": "", "PORT": ""})

        assert not any(arg.startswith("--host") for arg in argv)
        assert not any(arg.startswith("--port") for arg in argv)


class TestVersionCheck:
    @patch("arabase.backup.runner._server_major_version", return_value=16)
    @patch("arabase.backup.runner._pg_dump_major_version", return_value=15)
    def test_refuses_an_older_client_than_server(self, _client, _server):
        with pytest.raises(BackupError, match="refuses to dump a newer server"):
            run_backup(_config())

    @patch("arabase.backup.runner._server_major_version", return_value=15)
    @patch("arabase.backup.runner._pg_dump_major_version", return_value=16)
    @patch("arabase.backup.runner._prune", return_value=[])
    @patch("arabase.backup.runner._upload")
    @patch("arabase.backup.runner._client")
    @patch("arabase.backup.runner._dump_to_file", return_value=2048)
    def test_allows_a_newer_client(self, *_mocks):
        assert run_backup(_config()).size_bytes == 2048


class TestRunBackup:
    def test_refuses_to_run_unconfigured(self):
        with pytest.raises(BackupError, match="not configured"):
            run_backup(_config(bucket=""))

    @patch("arabase.backup.runner.check_versions", return_value=(15, 15))
    @patch("arabase.backup.runner._prune", return_value=[])
    @patch("arabase.backup.runner._upload")
    @patch("arabase.backup.runner._client")
    @patch("arabase.backup.runner._dump_to_file", return_value=4096)
    def test_uploads_privately_under_the_prefix(
        self, _dump, _client, upload, _prune, _versions
    ):
        result = run_backup(_config())

        assert result.key.startswith("postgres/jadawel-")
        assert result.key.endswith(".dump")
        assert upload.call_count == 1

    @patch("arabase.backup.runner.check_versions", return_value=(15, 15))
    @patch("arabase.backup.runner._client")
    @patch(
        "arabase.backup.runner._dump_to_file",
        side_effect=BackupError("pg_dump exited with 1"),
    )
    def test_does_not_upload_a_failed_dump(self, _dump, client, _versions):
        with pytest.raises(BackupError):
            run_backup(_config())

        client.return_value.upload_fileobj.assert_not_called()

    @patch("arabase.backup.runner.check_versions", return_value=(15, 15))
    @patch("arabase.backup.runner._prune", return_value=[])
    @patch("arabase.backup.runner._upload")
    @patch("arabase.backup.runner._client")
    @patch("arabase.backup.runner._dump_to_file")
    def test_removes_the_temporary_file_even_when_upload_fails(
        self, dump, _client, upload, _prune, _versions
    ):
        captured = {}

        def record(path):
            captured["path"] = path
            return 1024

        dump.side_effect = record
        upload.side_effect = RuntimeError("network down")

        with pytest.raises(RuntimeError):
            run_backup(_config())

        import os

        assert not os.path.exists(captured["path"])


class TestPrune:
    def _client_listing(self, objects):
        client = MagicMock()
        client.get_paginator.return_value.paginate.return_value = [
            {"Contents": objects}
        ]
        return client

    def test_deletes_only_objects_past_the_window(self):
        now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        client = self._client_listing(
            [
                {"Key": "postgres/old.dump", "LastModified": now - timedelta(days=20)},
                {"Key": "postgres/new.dump", "LastModified": now - timedelta(days=2)},
            ]
        )

        pruned = _prune(client, _config(retention_days=14), now)

        assert pruned == ["postgres/old.dump"]
        client.delete_object.assert_called_once_with(
            Bucket="jadawel-backups", Key="postgres/old.dump"
        )

    def test_keeps_everything_inside_the_window(self):
        now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        client = self._client_listing(
            [{"Key": "postgres/a.dump", "LastModified": now - timedelta(days=1)}]
        )

        assert _prune(client, _config(), now) == []
        client.delete_object.assert_not_called()


class TestTask:
    # Patched where it is used, not where it is defined: arabase.tasks binds
    # run_backup into its own namespace at import time.
    @patch("arabase.tasks.run_backup")
    def test_does_nothing_when_disabled(self, run, monkeypatch):
        monkeypatch.delenv("JADAWEL_BACKUP_ENABLED", raising=False)
        from arabase.tasks import backup_database

        assert backup_database() is None
        run.assert_not_called()

    @patch("arabase.tasks.run_backup")
    def test_runs_when_enabled(self, run, monkeypatch):
        monkeypatch.setenv("JADAWEL_BACKUP_ENABLED", "true")
        run.return_value = MagicMock(key="postgres/a.dump", size_bytes=99)
        from arabase.tasks import backup_database

        assert backup_database() == {"key": "postgres/a.dump", "size_bytes": 99}
        run.assert_called_once()
