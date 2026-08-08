"""Back the database up to object storage.

Jadawel's own ``backup_jadawel`` refuses to run when ``DATABASE_URL`` is set,
which is how every managed deployment connects, so this is the command to use
in production::

    ./jadawel backend-cmd-with-db manage backup_database
"""

from django.core.management.base import BaseCommand, CommandError

from arabase.backup.config import BackupConfig
from arabase.backup.runner import BackupError, check_versions, run_backup


class Command(BaseCommand):
    help = "Dump the database with pg_dump and upload it to S3-compatible storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help=(
                "Validate the configuration and the pg_dump/server versions "
                "without dumping anything."
            ),
        )

    def handle(self, *args, **options):
        config = BackupConfig.from_env()

        if options["check"]:
            errors = config.validation_errors()
            if errors:
                raise CommandError("Backup is not configured: " + " ".join(errors))
            try:
                client, server = check_versions()
            except BackupError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(
                self.style.SUCCESS(
                    f"Configuration is valid. pg_dump {client} against server "
                    f"{server}; target s3://{config.bucket}/{config.prefix} "
                    f"keeping {config.retention_days} days."
                )
            )
            return

        try:
            result = run_backup(config)
        except BackupError as exc:
            raise CommandError(str(exc)) from exc

        megabytes = result.size_bytes / 1024 / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Uploaded {result.key} ({megabytes:.1f} MiB) in "
                f"{result.duration_seconds:.1f}s."
            )
        )
        if result.pruned_keys:
            self.stdout.write(f"Pruned {len(result.pruned_keys)} expired backup(s).")
