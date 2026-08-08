# Backup and restore

The production database is a CranL-managed PostgreSQL instance
(`jadawel-postgres`), reachable only from inside the project network at
`jadawel-postgres-kk5nq0:5432`. That shapes everything below.

## Why not `backup_jadawel`

Jadawel ships `manage.py backup_jadawel`, and it cannot be used here. It
refuses to start when `DATABASE_URL` is set
(`backend/docker/docker-entrypoint.sh:427-433`), which is exactly how this
deployment connects. The replacement is the fork's own
`manage.py backup_database`, in `backend/src/arabase/backup/`.

## What runs

| Piece | Location |
|---|---|
| Dump + upload + prune | `arabase/backup/runner.py` |
| Configuration | `arabase/backup/config.py` |
| Manual command | `arabase/management/commands/backup_database.py` |
| Scheduled task | `arabase.tasks.backup_database`, on the `export` queue |

A dump is `pg_dump --format=custom --compress=9`, uploaded to S3-compatible
storage with `ACL=private`, after which objects older than the retention
window are deleted.

Two deliberate choices worth knowing:

- **Backups never go through Django's `default_storage`.** That backend sets
  `AWS_DEFAULT_ACL = "public-read"` so user files can be served directly
  (`jadawel/config/settings/base.py:690`). A database dump written through it
  would be world-readable. The uploader builds its own boto3 client.
- **The credentials are separate from `AWS_*`.** The key that writes backups
  should not be a key any web request can reach, and it needs no read access
  to the media bucket.

## Configuration

Set these on the app in the CranL dashboard, then reload it.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `JADAWEL_BACKUP_ENABLED` | yes | `false` | Nothing is scheduled until this is true. |
| `JADAWEL_BACKUP_S3_BUCKET` | yes | — | |
| `JADAWEL_BACKUP_S3_ACCESS_KEY_ID` | yes | — | Write-only key if the provider supports it. |
| `JADAWEL_BACKUP_S3_SECRET_ACCESS_KEY` | yes | — | |
| `JADAWEL_BACKUP_S3_ENDPOINT_URL` | no | AWS | Set for R2, B2, MinIO, or any non-AWS provider. |
| `JADAWEL_BACKUP_S3_REGION` | no | — | |
| `JADAWEL_BACKUP_S3_PREFIX` | no | `postgres/` | A trailing slash is added if missing. |
| `JADAWEL_BACKUP_RETENTION_DAYS` | no | `14` | Age is taken from the object's `LastModified`. |
| `JADAWEL_BACKUP_CRONTAB` | no | `0 23 * * *` | 23:00 UTC is 02:00 in Riyadh. |
| `JADAWEL_BACKUP_S3_SSE` | no | — | e.g. `AES256`. Not every provider implements it. |
| `JADAWEL_BACKUP_TIMEOUT_SECONDS` | no | `3600` | `pg_dump` is killed past this. |

Verify without dumping anything:

```
./jadawel backend-cmd-with-db manage backup_database --check
```

That validates the credentials and compares the `pg_dump` version against the
server, which is the one failure that would otherwise only surface at 02:00.

## Taking a backup by hand

```
./jadawel backend-cmd-with-db manage backup_database
```

## Restoring

**Rehearse this before launch, into a scratch database — not into
production.** A backup nobody has restored is a hypothesis.

1. Download the dump.

   ```
   aws s3 cp s3://<bucket>/postgres/jadawel-<timestamp>.dump ./restore.dump
   ```

2. Create an empty target database. To rehearse, make a second managed
   Postgres in the same project and region rather than touching the live one.

3. Restore. `--clean --if-exists` makes the restore repeatable; drop them when
   restoring into a database that is already empty.

   ```
   pg_restore \
     --dbname="postgresql://user:password@host:5432/dbname" \
     --no-owner --no-privileges \
     --clean --if-exists \
     ./restore.dump
   ```

   The dump is taken with `--no-owner --no-privileges`, so it restores under
   whatever role you connect as and does not require the original `jadawel`
   role to exist.

4. Point a throwaway app at the restored database and confirm it boots,
   migrations report no pending work, and a dashboard renders.

### What a restore does *not* bring back

The dump covers the database only. User-uploaded files live in object storage
(or, until that is configured, on the container's ephemeral disk, where they
do not survive a redeploy — see the uploads finding in
`PRODUCTION_READINESS.md`). A database restore alone will leave file fields
pointing at objects that no longer exist.

## Version compatibility

The image installs `postgresql-client-15` (`deploy/all-in-one/Dockerfile:40`,
`POSTGRES_VERSION=15`). `pg_dump` refuses to dump a server newer than itself,
so if the managed instance is PostgreSQL 16 or later, `--check` fails with the
version it needs and the image has to install a matching client. This is
checked before every dump rather than at 02:00.
