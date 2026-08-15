from rest_framework import serializers

from arabase.backup.models import FREQUENCY_CHOICES, BackupRun


class BackupRunSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = BackupRun
        fields = (
            "id",
            "started_on",
            "finished_on",
            "duration_seconds",
            "status",
            "trigger",
            "key",
            "size_bytes",
            "media_key",
            "media_size_bytes",
            "pruned_count",
            "error",
        )
        read_only_fields = fields


class BackupHealthSerializer(serializers.Serializer):
    status = serializers.CharField(
        help_text=(
            "One of `ok`, `disabled`, `misconfigured`, `never_run`, "
            "`last_failed` or `overdue`."
        )
    )
    healthy = serializers.BooleanField()
    last_success_on = serializers.DateTimeField(allow_null=True)
    next_run_on = serializers.DateTimeField(allow_null=True)
    configuration_errors = serializers.ListField(child=serializers.CharField())
    last_run = BackupRunSerializer(allow_null=True)


class BackupScheduleSerializer(serializers.Serializer):
    frequency = serializers.ChoiceField(choices=FREQUENCY_CHOICES)
    crontab = serializers.CharField(read_only=True)


class BackupOverviewSerializer(serializers.Serializer):
    """Everything the admin section needs for its first paint."""

    enabled = serializers.BooleanField(
        help_text=(
            "Whether JADAWEL_BACKUP_ENABLED is set. The schedule below only "
            "decides how often once this is on."
        )
    )
    schedule = BackupScheduleSerializer()
    health = BackupHealthSerializer()


class UpdateBackupScheduleSerializer(serializers.Serializer):
    frequency = serializers.ChoiceField(
        choices=FREQUENCY_CHOICES,
        help_text="How often a backup is taken.",
    )


class RestoreBackupSerializer(serializers.Serializer):
    key = serializers.CharField(
        help_text="Object key of the dump to restore, from the run history."
    )
    target_database_url = serializers.CharField(
        help_text=(
            "A postgresql:// connection string for the database to restore "
            "into. Must not be the live database — the restore is a rehearsal "
            "tool, and switching over stays a manual step."
        )
    )


class RestoreBackupResponseSerializer(serializers.Serializer):
    key = serializers.CharField()
    target = serializers.CharField(help_text="The target, with the password removed.")
