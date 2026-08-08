"""Off-host database backups for the Jadawel fork.

Jadawel's own ``backup_jadawel`` command refuses to run when ``DATABASE_URL``
is set, which is precisely how the CranL deployment connects, so it cannot be
used in production. This package is the additive replacement: it dumps the
database with ``pg_dump`` and uploads the result to S3-compatible object
storage, on a Celery beat schedule.

Nothing here writes through Django's ``default_storage``. That backend is
configured with ``AWS_DEFAULT_ACL = "public-read"``
(``jadawel/config/settings/base.py:690``) so that user files can be served
directly, and a database dump uploaded with that ACL would be world-readable.
The uploader in ``runner`` builds its own boto3 client and sets
``ACL="private"`` explicitly.
"""
