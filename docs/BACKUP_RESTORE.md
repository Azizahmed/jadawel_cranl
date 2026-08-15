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

## Where backups are stored

Backups must stay inside Saudi Arabia, which is the premise of the whole fork
(`AGENTS.md`). That is a stronger constraint than it first looks, because it
rules out most object storage:

| Provider | Nearest region | Verdict |
|---|---|---|
| CranL object storage | Riyadh / Saudi-4 | **The only in-country option.** Postgres, Redis and the `jadawel-media` bucket already live there (`cranl_fix.md:33`). |
| AWS S3 | Bahrain, UAE | Gulf, not Saudi. |
| Cloudflare R2, Backblaze B2 | — | No Middle East region at all. |

So the backup target is a CranL bucket in the same Riyadh region as the
database, which also keeps the dump on the internal network.

One known obstacle: creating a bucket token currently fails with
`Quota limit exceeded. You can create no more than 50 tokens`
(`cranl_fix.md:224`). Existing unused tokens have to be deleted in the CranL
dashboard first — the MCP exposes no object-storage tooling, so this is a
dashboard-only step.

Prefer a **separate bucket** from `jadawel-media` rather than a prefix inside
it. User files are served public-read by design; keeping database dumps in a
different bucket means no bucket-level policy can ever expose them. If they
must share a bucket, `validation_errors()` refuses to run without a prefix,
and the uploader still sets `ACL=private` per object.

## Recovery point

A logical dump on a schedule means the recovery point is the last dump, not
the last transaction: with the default daily crontab, up to 24 hours of writes
are lost in a total-loss scenario. The database is small, so the cheap
improvement is simply to dump more often —
`JADAWEL_BACKUP_CRONTAB="0 */6 * * *"` takes that to 6 hours at four times the
storage. Point-in-time recovery would need WAL archiving, which the managed
instance does not expose.

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
| `JADAWEL_BACKUP_S3_PREFIX` | no | `postgres/` | A trailing slash is added if missing. **Must not be empty** — retention deletes under this prefix, so an empty one means the whole bucket. Validation rejects it. |
| `JADAWEL_BACKUP_RETENTION_DAYS` | no | `14` | Age is taken from the object's `LastModified`. |
| `JADAWEL_BACKUP_CRONTAB` | no | `0 23 * * *` | 23:00 UTC is 02:00 in Riyadh. |
| `JADAWEL_BACKUP_S3_SSE` | no | — | e.g. `AES256`. Not every provider implements it. |
| `JADAWEL_BACKUP_TIMEOUT_SECONDS` | no | `3600` | `pg_dump` is killed past this. The Celery soft limit is derived from it. |
| `JADAWEL_BACKUP_INCLUDE_MEDIA` | no | on, unless `AWS_STORAGE_BUCKET_NAME` is set | Archives user-uploaded files alongside the dump. Turn it off only when the files already live in object storage. |

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

### User files

The database is not a restore point on its own. Every file cell, export and
uploaded image in it names a file under `MEDIA_ROOT`, so a database restored
without those files comes back with broken references throughout.

When `JADAWEL_BACKUP_INCLUDE_MEDIA` is on, each run uploads a second object
beside the dump, stamped with the same timestamp:

```
postgres/jadawel-20260815T230000Z.dump
postgres/jadawel-20260815T230000Z.media.tar.gz
```

Restore them as a pair — matching timestamps are what make the two halves a
single point in time. The archive unpacks to a `media/` directory:

```
tar -xzf jadawel-20260815T230000Z.media.tar.gz -C /tmp/restore
# then copy /tmp/restore/media/* over MEDIA_ROOT
```

Retention removes media archives on the same schedule as dumps, and only ever
deletes objects matching the `jadawel-<timestamp>` naming above — anything else
sharing the bucket is left alone.

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
