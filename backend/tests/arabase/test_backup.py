import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from arabase.backup import runner
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
        acl=None,
        include_media=False,
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

    def test_sends_no_acl_unless_one_is_configured(self, monkeypatch):
        monkeypatch.delenv("JADAWEL_BACKUP_S3_ACL", raising=False)

        assert BackupConfig.from_env().acl is None

    def test_reads_an_explicit_acl(self, monkeypatch):
        monkeypatch.setenv("JADAWEL_BACKUP_S3_ACL", "private")

        assert BackupConfig.from_env().acl == "private"


class TestUpload:
    """What goes on the PutObject call.

    An ACL header is the one thing here that a storage provider will reject the
    whole upload over. Cloudflare R2 does not implement object ACLs, and an AWS
    bucket created since April 2023 defaults to Object Ownership `bucket owner
    enforced`, which answers `x-amz-acl` with AccessControlListNotSupported. So
    the default has to be to send nothing.
    """

    def _upload_extra_args(self, config, tmp_path):
        path = tmp_path / "dump"
        path.write_bytes(b"dump")
        client = MagicMock()

        runner._upload(client, config, str(path), "postgres/jadawel.dump")

        return client.upload_fileobj.call_args.kwargs["ExtraArgs"]

    def test_omits_the_acl_by_default(self, tmp_path):
        assert "ACL" not in self._upload_extra_args(_config(), tmp_path)

    def test_sends_an_acl_when_one_is_configured(self, tmp_path):
        extra = self._upload_extra_args(_config(acl="private"), tmp_path)

        assert extra["ACL"] == "private"

    def test_sends_encryption_only_when_configured(self, tmp_path):
        assert "ServerSideEncryption" not in self._upload_extra_args(
            _config(), tmp_path
        )
        assert (
            self._upload_extra_args(_config(sse="AES256"), tmp_path)[
                "ServerSideEncryption"
            ]
            == "AES256"
        )


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


class TestPrefixSafety:
    def test_an_empty_prefix_is_rejected(self):
        """Retention deletes under the prefix, so an empty one is the whole
        bucket. The job must refuse to run rather than discover that at 2am."""

        errors = _config(prefix="").validation_errors()

        assert any("JADAWEL_BACKUP_S3_PREFIX" in error for error in errors)

    def test_a_prefix_makes_the_config_usable(self):
        assert _config(prefix="postgres/").validation_errors() == []


class TestPrune:
    def _client_listing(self, objects):
        client = MagicMock()
        client.get_paginator.return_value.paginate.return_value = [
            {"Contents": objects}
        ]
        return client

    def test_deletes_only_objects_past_the_window(self):
        now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        old = "postgres/jadawel-20260719T230000Z.dump"
        new = "postgres/jadawel-20260806T230000Z.dump"
        client = self._client_listing(
            [
                {"Key": old, "LastModified": now - timedelta(days=20)},
                {"Key": new, "LastModified": now - timedelta(days=2)},
            ]
        )

        pruned = _prune(client, _config(retention_days=14), now)

        assert pruned == [old]
        client.delete_object.assert_called_once_with(Bucket="jadawel-backups", Key=old)

    def test_keeps_everything_inside_the_window(self):
        now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        client = self._client_listing(
            [
                {
                    "Key": "postgres/jadawel-20260807T230000Z.dump",
                    "LastModified": now - timedelta(days=1),
                }
            ]
        )

        assert _prune(client, _config(), now) == []
        client.delete_object.assert_not_called()

    def test_never_deletes_an_object_it_did_not_write(self):
        """Retention lists by prefix, so anything else sharing that prefix is in
        range of the delete. Age alone must not be enough to remove it."""

        now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        client = self._client_listing(
            [
                {
                    "Key": "postgres/jadawel-20260719T230000Z.dump",
                    "LastModified": now - timedelta(days=20),
                },
                {
                    "Key": "postgres/quarterly-report.xlsx",
                    "LastModified": now - timedelta(days=400),
                },
                {"Key": "postgres/", "LastModified": now - timedelta(days=400)},
            ]
        )

        pruned = _prune(client, _config(retention_days=14), now)

        assert pruned == ["postgres/jadawel-20260719T230000Z.dump"]
        assert client.delete_object.call_count == 1


class TestTask:
    # Patched where it is used, not where it is defined: arabase.tasks binds
    # run_backup into its own namespace at import time.
    @patch("arabase.tasks.run_backup")
    def test_does_nothing_when_disabled(self, run, monkeypatch):
        monkeypatch.delenv("JADAWEL_BACKUP_ENABLED", raising=False)
        from arabase.tasks import backup_database

        assert backup_database() is None
        run.assert_not_called()

    # Needs the database because a run is now recorded as a BackupRun row: a
    # failed backup uploads nothing, so without a row a failure would be
    # indistinguishable from a backup that never ran.
    @pytest.mark.django_db
    @patch("arabase.tasks.run_backup")
    def test_runs_when_enabled(self, run, monkeypatch):
        monkeypatch.setenv("JADAWEL_BACKUP_ENABLED", "true")
        run.return_value = MagicMock(
            key="postgres/a.dump",
            size_bytes=99,
            media_key=None,
            media_size_bytes=0,
            pruned_keys=[],
        )
        from arabase.backup.models import BackupRun
        from arabase.tasks import backup_database

        assert backup_database() == {"key": "postgres/a.dump", "size_bytes": 99}
        run.assert_called_once()

        recorded = BackupRun.objects.first()
        assert recorded.status == BackupRun.STATUS_SUCCESS
        assert recorded.key == "postgres/a.dump"


class TestMediaArchive:
    """A database dump on its own is not a restore point.

    Every file cell, export and uploaded image in the database names a file on
    disk, so a database restored without those files comes back with broken
    references throughout.
    """

    @patch("arabase.backup.runner.check_versions", return_value=(15, 15))
    @patch("arabase.backup.runner._prune", return_value=[])
    @patch("arabase.backup.runner._archive_media", return_value=2048)
    @patch("arabase.backup.runner._upload")
    @patch("arabase.backup.runner._client")
    @patch("arabase.backup.runner._dump_to_file", return_value=4096)
    def test_uploads_user_files_beside_the_dump(
        self, _dump, _client, upload, _archive, _prune, _versions
    ):
        result = run_backup(_config(include_media=True))

        assert upload.call_count == 2
        # Same timestamp on both, so the two halves of the restore point are
        # unambiguously paired.
        stamp = result.key.removeprefix("postgres/jadawel-").removesuffix(".dump")
        assert result.media_key == f"postgres/jadawel-{stamp}.media.tar.gz"
        assert result.media_size_bytes == 2048

    @patch("arabase.backup.runner.check_versions", return_value=(15, 15))
    @patch("arabase.backup.runner._prune", return_value=[])
    @patch("arabase.backup.runner._archive_media")
    @patch("arabase.backup.runner._upload")
    @patch("arabase.backup.runner._client")
    @patch("arabase.backup.runner._dump_to_file", return_value=4096)
    def test_skips_user_files_when_disabled(
        self, _dump, _client, upload, archive, _prune, _versions
    ):
        result = run_backup(_config(include_media=False))

        archive.assert_not_called()
        assert upload.call_count == 1
        assert result.media_key is None

    @patch("arabase.backup.runner.check_versions", return_value=(15, 15))
    @patch("arabase.backup.runner._prune", return_value=[])
    @patch("arabase.backup.runner._upload")
    @patch("arabase.backup.runner._client")
    @patch("arabase.backup.runner._dump_to_file", return_value=4096)
    def test_removes_the_temporary_archive(
        self, _dump, _client, _upload, _prune, _versions, tmp_path, settings
    ):
        media_root = tmp_path / "media"
        media_root.mkdir()
        (media_root / "user_files").mkdir()
        (media_root / "user_files" / "invoice.pdf").write_bytes(b"%PDF-1.4 ...")
        settings.MEDIA_ROOT = str(media_root)

        captured = []
        real_archive = runner._archive_media

        def record(path):
            captured.append(path)
            return real_archive(path)

        with patch("arabase.backup.runner._archive_media", side_effect=record):
            result = run_backup(_config(include_media=True))

        assert result.media_size_bytes > 0
        # The archive is written to disk before upload; it must not be left there.
        assert captured and not os.path.exists(captured[0])

    def test_media_archive_reports_a_missing_root_as_a_backup_error(
        self, settings, tmp_path
    ):
        settings.MEDIA_ROOT = str(tmp_path / "does-not-exist")

        with pytest.raises(BackupError, match="MEDIA_ROOT"):
            # Never reached: the root is checked before the archive is opened.
            runner._archive_media(str(tmp_path / "unused.tar.gz"))


class TestMediaRetention:
    def test_a_media_archive_is_pruned_like_a_dump(self):
        now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        client = MagicMock()
        client.get_paginator.return_value.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "postgres/jadawel-20260719T230000Z.media.tar.gz",
                        "LastModified": now - timedelta(days=20),
                    },
                    {
                        "Key": "postgres/holiday-photos.tar.gz",
                        "LastModified": now - timedelta(days=20),
                    },
                ]
            }
        ]

        pruned = _prune(client, _config(retention_days=14), now)

        assert pruned == ["postgres/jadawel-20260719T230000Z.media.tar.gz"]
