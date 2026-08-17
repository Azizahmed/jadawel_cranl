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
| `JADAWEL_BACKUP_CRONTAB` | no | `0 23 * * *` | Fallback only. The frequency is set in **Admin → Backup** and stored in the database; this applies when that row cannot be read. |
| `JADAWEL_BACKUP_S3_SSE` | no | — | e.g. `AES256`. Not every provider implements it. |
| `JADAWEL_BACKUP_S3_ACL` | no | — | Leave empty. See [Object ACLs](#object-acls). |
| `JADAWEL_BACKUP_TIMEOUT_SECONDS` | no | `3600` | `pg_dump` is killed past this. The Celery soft limit is derived from it. |
| `JADAWEL_BACKUP_INCLUDE_MEDIA` | no | on, unless `AWS_STORAGE_BUCKET_NAME` is set | Archives user-uploaded files alongside the dump. Turn it off only when the files already live in object storage. |

### Object ACLs

Uploads send **no ACL header** unless `JADAWEL_BACKUP_S3_ACL` is set, and it
should stay unset. Both likely targets refuse the header:

- Cloudflare R2 does not implement object ACLs at all.
- An AWS bucket created since April 2023 defaults to Object Ownership *bucket
  owner enforced*, which answers `x-amz-acl` with `AccessControlListNotSupported`.

Sending `private` was doing nothing useful even where it was accepted — an
object is private unless a bucket policy says otherwise — while making the
upload fail outright everywhere else. Set this only for a legacy bucket that
still has ACLs switched on.

### Cloudflare R2

R2 is S3-compatible through `boto3` with two provider-specific values:

```
JADAWEL_BACKUP_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
JADAWEL_BACKUP_S3_REGION=auto
```

`auto` is not a placeholder — it is the only region R2 accepts, and `boto3`
requires *some* region to sign the request.

Create the API token as **Object Read & Write scoped to the backup bucket**.
Retention needs delete, which R2 includes in write; nothing here needs account
scope. The token secret is shown once.

Note that R2 is not inside Saudi Arabia. For a deployment where residency is
the point, Google Cloud Storage in `me-central2` (Dammam) or Oracle Object
Storage in Jeddah are the S3-compatible options that keep the dumps in-country.

Verify without dumping anything:

```
./jadawel backend-cmd-with-db manage backup_database --check
```

That validates the credentials and compares the `pg_dump` version against the
server, which is the one failure that would otherwise only surface at 02:00.

### Postgres client version

`pg_dump` refuses to dump a server newer than itself, so the client in the
image has to be at least as new as the database. Two settings look like they
control this and only one of them does:

| Setting | What it is |
|---|---|
| `POSTGRES_CLIENT_VERSION` | `pg_dump` and `pg_restore`. Raise this. |
| `POSTGRES_VERSION` | The **embedded** Postgres server. Leave it alone. |

They are separate on purpose. The database being backed up is CranL's managed
instance, not the embedded server, and the two are on different majors. Raising
`POSTGRES_VERSION` to fix a dump would also mean a newer embedded server, which
will not start on a data directory an older major initialised — so it trades a
failed backup for a dead database.

Raising the client is free: `pg_dump` reads older servers happily and refuses
only newer ones. The image ships 18 for that headroom.

Note that `/usr/bin/pg_dump` is Debian's `pg_wrapper`, which picks a major from
the default *cluster* rather than from the server being contacted — the
embedded one, in this image. `arabase.backup.runner.client_binary()` therefore
resolves `/usr/lib/postgresql/*/bin/` itself and takes the highest major, so
installing a newer client is enough to change what actually runs.

## The admin section

**Admin → Backup** is the page to look at, and the reason it exists is that a
backup which quietly stopped running looks exactly like one that is working —
right up to the day it is needed.

It shows:

- **Health**, as a banner. `disabled` is neutral, because switched off on
  purpose is a legitimate state. `misconfigured` is an error, because the job is
  scheduled and will fail every time it fires. `overdue` is judged against the
  chosen frequency, so six hours late matters on an hourly schedule and does not
  on a weekly one, and it outranks a failed last run — being a month stale is
  the more urgent fact.
- **Frequency** — hourly, daily or weekly. Saving republishes the schedule to
  RedBeat, so it applies immediately rather than on the next redeploy. If that
  republish fails the change still applies on the next worker restart.
- **History**, including failed attempts. This is why runs are rows in the
  database rather than a listing of the bucket: a failed run uploads nothing, so
  a bucket listing cannot distinguish it from a run that never started.
- **Restore**, which never writes over the live database. See below.

## Taking a backup by hand

```
./jadawel backend-cmd-with-db manage backup_database
```

## Restoring

**Rehearse this before launch, into a scratch database — not into
production.** A backup nobody has restored is a hypothesis.

The **Restore** button in Admin → Backup does exactly this and nothing more: it
downloads the dump and restores it into a database you nominate. The target is
compared against the running connection and refused if it matches, so there is
no code path from that button to the live database. A restore has no undo — it
destroys the rows you would need to recover from a wrong choice — and the one
moment anyone reaches for it is a moment of panic, so switching over stays a
deliberate human step taken with the restored copy in front of you.

The manual procedure below is the same sequence, and is what to use when the app
itself is the thing that is down.

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
