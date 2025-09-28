import pytest
import os
from unittest.mock import MagicMock
from botocore.exceptions import ClientError
from src.services.s3_service import S3Service
from src.exceptions import S3Error

@pytest.fixture
def s3_service_instance(mocked_s3):
    service = S3Service(s3_client=mocked_s3)
    return service


def test_s3_service_init_no_bucket_name():
    if "IMAGE_BUCKET_NAME" in os.environ:
        del os.environ["IMAGE_BUCKET_NAME"]
    with pytest.raises(ValueError, match="IMAGE_BUCKET_NAME environment variable not set."):
        S3Service(s3_client=MagicMock())


def test_upload_file_success(s3_service_instance):
    file_bytes = b"test_image_data"
    object_name = "test-image.jpg"
    content_type = "image/jpeg"
    result = s3_service_instance.upload_file(file_bytes, object_name, content_type)
    assert result == object_name
    response = s3_service_instance.s3_client.get_object(
        Bucket=s3_service_instance.bucket_name, Key=object_name
    )
    assert response["Body"].read() == file_bytes


def test_upload_file_s3_error(s3_service_instance):
    s3_service_instance.s3_client.put_object = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "S3 error"}}, "PutObject")
    )
    with pytest.raises(S3Error, match="Failed to upload"):
        s3_service_instance.upload_file(b"data", "fail.jpg", "image/jpeg")


def test_get_file_url_success(s3_service_instance):
    object_name = "existing-image.png"
    s3_service_instance.s3_client.put_object(
        Bucket=s3_service_instance.bucket_name, Key=object_name, Body=b"data"
    )
    url = s3_service_instance.get_file_url(object_name)
    assert object_name in url
    assert s3_service_instance.bucket_name in url


def test_get_file_url_localstack_hostname(set_localstack_env_vars, s3_service_instance):
    object_name = "localstack-image.gif"
    s3_service_instance.s3_client.put_object(
        Bucket=s3_service_instance.bucket_name, Key=object_name, Body=b"data"
    )
    s3_service_instance.s3_client.generate_presigned_url = MagicMock(
        return_value=f"http://{os.environ['LOCALSTACK_HOSTNAME']}:4566/{s3_service_instance.bucket_name}/{object_name}"
    )
    url = s3_service_instance.get_file_url(object_name)
    assert "localhost" in url
    assert os.environ["LOCALSTACK_HOSTNAME"] not in url


def test_get_file_url_s3_error(s3_service_instance):
    s3_service_instance.s3_client.generate_presigned_url = MagicMock(
        side_effect=ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "GetObject")
    )
    with pytest.raises(S3Error, match="Failed to generate URL"):
        s3_service_instance.get_file_url("non-existent.jpg")


def test_delete_file_success(s3_service_instance):
    object_name = "to-delete.txt"
    s3_service_instance.s3_client.put_object(
        Bucket=s3_service_instance.bucket_name, Key=object_name, Body=b"data"
    )
    s3_service_instance.delete_file(object_name)
    with pytest.raises(ClientError) as excinfo:
        s3_service_instance.s3_client.get_object(
            Bucket=s3_service_instance.bucket_name, Key=object_name
        )
    assert excinfo.value.response["Error"]["Code"] == "NoSuchKey"


def test_delete_file_s3_error(s3_service_instance):
    s3_service_instance.s3_client.delete_object = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "S3 error"}}, "DeleteObject")
    )
    with pytest.raises(S3Error, match="Failed to delete"):
        s3_service_instance.delete_file("fail.txt")