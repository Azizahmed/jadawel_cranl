import json
import os
import zipfile
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

import pytest

from jadawel.core.handler import CoreHandler
from jadawel.core.import_export.exceptions import (
    ImportExportResourceInvalidFile,
    ImportExportResourceUntrustedSignature,
)
from jadawel.core.import_export.handler import ImportExportHandler
from jadawel.test_utils.zip_helpers import (
    change_file_content_in_zip,
    get_file_content_from_zip,
)

SOURCES_PATH = os.path.join(
    settings.BASE_DIR, "../../../tests/jadawel/api/import_export/sources"
)
INTERESTING_DB_EXPORT_PATH = f"{SOURCES_PATH}/interesting_database_export.zip"


def make_zip(files):
    stream = BytesIO()
    with zipfile.ZipFile(
        stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zip_file:
        for name, content in files.items():
            zip_file.writestr(name, content)
    stream.seek(0)
    return stream


@pytest.mark.import_export_workspace
@override_settings(IMPORT_ARCHIVE_MAX_JSON_SIZE_BYTES=1024)
def test_validate_manifest_rejects_zip_bomb_before_json_decode():
    manifest = json.dumps(
        {
            "version": "1.0.0",
            "configuration": {"only_structure": True},
            "applications": {},
            "checksums": {},
            "padding": "A" * 4096,
        }
    )
    stream = make_zip({"manifest.json": manifest})

    with zipfile.ZipFile(stream) as zip_file:
        with patch("jadawel.core.import_export.handler.json.loads") as json_loads:
            with pytest.raises(
                ImportExportResourceInvalidFile,
                match="Manifest file exceeds the allowed size limit",
            ):
                ImportExportHandler().validate_manifest(zip_file)

    json_loads.assert_not_called()


@pytest.mark.import_export_workspace
@override_settings(
    IMPORT_ARCHIVE_MAX_UNCOMPRESSED_SIZE_BYTES=128,
    IMPORT_ARCHIVE_MAX_JSON_SIZE_BYTES=1024,
)
def test_validate_manifest_rejects_aggregate_uncompressed_size():
    stream = make_zip(
        {
            "manifest.json": "{}",
            "first.data": b"A" * 64,
            "second.data": b"B" * 64,
        }
    )

    with zipfile.ZipFile(stream) as zip_file:
        with pytest.raises(
            ImportExportResourceInvalidFile,
            match="Archive uncompressed size exceeds the allowed limit",
        ):
            ImportExportHandler().validate_manifest(zip_file)


@pytest.mark.import_export_workspace
@override_settings(
    IMPORT_ARCHIVE_MAX_UNCOMPRESSED_SIZE_BYTES=8192,
    IMPORT_ARCHIVE_MAX_JSON_SIZE_BYTES=1024,
)
def test_validate_manifest_rejects_oversized_application_json():
    manifest = json.dumps(
        {
            "version": "1.0.0",
            "configuration": {"only_structure": True},
            "applications": {
                "database": {
                    "version": "1.0.0",
                    "configuration": {},
                    "items": [
                        {
                            "id": 1,
                            "type": "database",
                            "name": "Database",
                            "uuid": "application-uuid",
                            "files": {"schema": "database.json"},
                        }
                    ],
                }
            },
            "checksums": {"database.json": "unused-by-manifest-validation"},
            "total_files": 2,
        }
    )
    stream = make_zip(
        {
            "manifest.json": manifest,
            "database.json": b"A" * 2048,
        }
    )

    with zipfile.ZipFile(stream) as zip_file:
        with pytest.raises(
            ImportExportResourceInvalidFile,
            match="Application data file database.json exceeds the allowed size limit",
        ):
            ImportExportHandler().validate_manifest(zip_file)


@pytest.mark.import_export_workspace
@pytest.mark.django_db(transaction=True)
def test_import_without_signature_and_check_enabled(
    data_fixture, use_tmp_media_root, tmp_path
):
    user = data_fixture.create_user()

    data_fixture.create_import_export_trusted_source()
    zip_name = "interesting_database_without_signature_disabled_check.zip"

    resource = data_fixture.create_import_export_resource(
        created_by=user, original_name=zip_name, is_valid=True
    )

    new_zip_path = change_file_content_in_zip(
        INTERESTING_DB_EXPORT_PATH,
        f"{tmp_path}/{zip_name}",
        "manifest_signature.json",
        "",
    )

    with open(new_zip_path, "rb") as export_file:
        content = export_file.read()
        data_fixture.create_import_export_resource_file(
            resource=resource, content=content
        )

    with open(new_zip_path, "rb") as zip_file_handle:
        with zipfile.ZipFile(zip_file_handle, "r") as zip_file:
            with pytest.raises(ImportExportResourceInvalidFile) as err:
                ImportExportHandler().validate_manifest(
                    zip_file=zip_file,
                )
    assert str(err.value) == "Signature file is corrupted."


@pytest.mark.import_export_workspace
@pytest.mark.django_db(transaction=True)
def test_import_without_signature_and_check_disabled(
    data_fixture, use_tmp_media_root, tmp_path
):
    user = data_fixture.create_user()

    core_settings = CoreHandler().get_settings()
    core_settings.verify_import_signature = False
    core_settings.save()

    data_fixture.create_import_export_trusted_source()
    zip_name = "interesting_database_without_signature_enabled_check.zip"

    resource = data_fixture.create_import_export_resource(
        created_by=user, original_name=zip_name, is_valid=True
    )

    new_zip_path = change_file_content_in_zip(
        INTERESTING_DB_EXPORT_PATH,
        f"{tmp_path}/{zip_name}",
        "manifest_signature.json",
        "",
    )

    with open(new_zip_path, "rb") as export_file:
        content = export_file.read()
        data_fixture.create_import_export_resource_file(
            resource=resource, content=content
        )

    with open(new_zip_path, "rb") as zip_file_handle:
        with zipfile.ZipFile(zip_file_handle, "r") as zip_file:
            result = ImportExportHandler().validate_manifest(
                zip_file=zip_file,
            )
    assert result is not None


@pytest.mark.import_export_workspace
@pytest.mark.django_db(transaction=True)
def test_import_without_signature_data(data_fixture, use_tmp_media_root, tmp_path):
    user = data_fixture.create_user()

    data_fixture.create_import_export_trusted_source()

    zip_name = "interesting_database_without_signature_data.zip"

    resource = data_fixture.create_import_export_resource(
        created_by=user, original_name=zip_name, is_valid=True
    )

    content = get_file_content_from_zip(
        INTERESTING_DB_EXPORT_PATH, "manifest_signature.json"
    )

    signature_data = json.loads(content)
    signature_data.pop("signature")

    new_zip_path = change_file_content_in_zip(
        INTERESTING_DB_EXPORT_PATH,
        f"{tmp_path}/{zip_name}",
        "manifest_signature.json",
        json.dumps(signature_data),
    )

    with open(new_zip_path, "rb") as export_file:
        content = export_file.read()
        data_fixture.create_import_export_resource_file(
            resource=resource, content=content
        )

    with open(new_zip_path, "rb") as zip_file_handle:
        with zipfile.ZipFile(zip_file_handle, "r") as zip_file:
            with pytest.raises(ImportExportResourceInvalidFile) as err:
                ImportExportHandler().validate_manifest(
                    zip_file=zip_file,
                )
    assert str(err.value) == "Signature verification failed."


@pytest.mark.import_export_workspace
@pytest.mark.django_db(transaction=True)
def test_import_no_trusted_source(data_fixture, use_tmp_media_root, tmp_path):
    user = data_fixture.create_user()

    data_fixture.create_import_export_resource(
        created_by=user, original_name="interesting_database.zip", is_valid=True
    )

    with open(INTERESTING_DB_EXPORT_PATH, "rb") as zip_file_handle:
        with zipfile.ZipFile(zip_file_handle, "r") as zip_file:
            with pytest.raises(ImportExportResourceUntrustedSignature) as err:
                ImportExportHandler().validate_manifest(
                    zip_file=zip_file,
                )
    assert str(err.value) == "Signature public key is not trusted."
