import pytest
import json
import base64
from unittest.mock import MagicMock, patch
from src.handlers import upload_image, list_images, get_image, delete_image
from src.exceptions import (
    InvalidRequestError,
    S3Error,
    DatabaseError,
    ImageNotFoundError,
)

@pytest.fixture(autouse=True)
def mock_services(monkeypatch, set_env_vars):
    """Automatically mock services and set environment variables for all handler tests."""
    mock_s3 = MagicMock()
    mock_dynamodb = MagicMock()
    monkeypatch.setattr('src.handlers.decorators._s3_service', mock_s3)
    monkeypatch.setattr('src.handlers.decorators._dynamodb_service', mock_dynamodb)
    return mock_s3, mock_dynamodb

@pytest.fixture
def mock_context():
    """Mock Lambda context object."""
    return MagicMock()

@patch('time.time', return_value=1678886400)
def test_upload_image_success(mock_time, mock_services, mock_context):
    mock_s3_service, mock_dynamodb_service = mock_services
    mock_uuid_obj = MagicMock()
    mock_uuid_obj.__str__.return_value = 'test-image-id'

    mock_file = MagicMock()
    mock_file.filename = "test.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.read.return_value = b"image_data"

    mock_form = {"description": "A test image", "tags": "test,mock"}
    mock_files = {"file": mock_file}

    with patch('src.handlers.upload_image.uuid.uuid4', return_value=mock_uuid_obj), \
         patch('src.handlers.upload_image.parse_multipart', return_value=(mock_form, mock_files)):
        event = {"headers": {"Content-Type": "multipart/form-data; boundary=mock"}, "body": "mock_body"}
        response = upload_image.handler(event, mock_context)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["message"] == "Image uploaded successfully"
        assert body["imageId"] == "test-image-id"

        mock_s3_service.upload_file.assert_called_once_with(
            b"image_data", "test-image-id-test.jpg", "image/jpeg"
        )
        mock_dynamodb_service.put_item.assert_called_once()
        metadata = mock_dynamodb_service.put_item.call_args[0][0]
        assert metadata["imageId"] == "test-image-id"
        assert metadata["filename"] == "test.jpg"
        assert metadata["description"] == "A test image"
        assert metadata["tags"] == ["test", "mock"]
        assert metadata["uploadTimestamp"] == 1678886400


def test_upload_image_missing_file_part(mock_context):
    with patch('src.handlers.upload_image.parse_multipart', return_value=({}, {})):
        event = {"headers": {"Content-Type": "multipart/form-data; boundary=mock"}, "body": "mock_body"}
        response = upload_image.handler(event, mock_context)
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["message"] == "File part 'file' is required."


def test_upload_image_invalid_request_error(mock_context):
    with patch('src.handlers.upload_image.parse_multipart', side_effect=InvalidRequestError("Bad format")):
        event = {"headers": {}, "body": "mock_body"}
        response = upload_image.handler(event, mock_context)
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["message"] == "Bad format"


def test_upload_image_s3_error(mock_services, mock_context):
    mock_s3_service, _ = mock_services
    mock_s3_service.upload_file.side_effect = S3Error("S3 upload failed")
    mock_file = MagicMock(filename="test.jpg", content_type="image/jpeg", read=lambda: b"data")
    with patch('src.handlers.upload_image.parse_multipart', return_value=({}, {"file": mock_file})):
        event = {"headers": {"Content-Type": "multipart/form-data; boundary=mock"}, "body": "mock_body"}
        response = upload_image.handler(event, mock_context)
        assert response["statusCode"] == 500
        assert json.loads(response["body"])["message"] == "A service error occurred."


def test_upload_image_database_error(mock_services, mock_context):
    mock_s3_service, mock_dynamodb_service = mock_services
    mock_dynamodb_service.put_item.side_effect = DatabaseError("DB put failed")
    mock_file = MagicMock(filename="test.jpg", content_type="image/jpeg", read=lambda: b"data")
    with patch('src.handlers.upload_image.parse_multipart', return_value=({}, {"file": mock_file})):
        event = {"headers": {"Content-Type": "multipart/form-data; boundary=mock"}, "body": "mock_body"}
        response = upload_image.handler(event, mock_context)
        assert response["statusCode"] == 500
        assert json.loads(response["body"])["message"] == "A service error occurred."


def test_upload_image_generic_exception(mock_context):
    with patch('src.handlers.upload_image.parse_multipart', side_effect=Exception("Unexpected error")):
        event = {"headers": {}, "body": "mock_body"}
        response = upload_image.handler(event, mock_context)
        assert response["statusCode"] == 500
        assert json.loads(response["body"])["message"] == "Internal server error"


def test_list_images_success_scan(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.scan_items.return_value = ([{"imageId": "1", "filename": "a.jpg"}], None)
    event = {"queryStringParameters": None}
    response = list_images.handler(event, mock_context)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body["items"]) == 1
    assert body["items"][0]["imageId"] == "1"
    mock_dynamodb_service.scan_items.assert_called_once_with(None)


def test_list_images_success_get_item(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.return_value = {"imageId": "2", "filename": "b.png"}
    event = {"queryStringParameters": {"imageId": "2"}}
    response = list_images.handler(event, mock_context)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body["items"]) == 1
    assert body["items"][0]["imageId"] == "2"
    mock_dynamodb_service.get_item.assert_called_once_with("2")


def test_list_images_success_query_content_type(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.query_by_content_type.return_value = ([{"imageId": "3", "contentType": "image/gif"}], None)
    event = {"queryStringParameters": {"contentType": "image/gif"}}
    response = list_images.handler(event, mock_context)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body["items"]) == 1
    assert body["items"][0]["imageId"] == "3"
    mock_dynamodb_service.query_by_content_type.assert_called_once_with("image/gif", None)


def test_list_images_pagination(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.scan_items.return_value = (
        [{"imageId": "4"}],
        {"imageId": "4_last"},
    )
    event = {"queryStringParameters": None}
    response = list_images.handler(event, mock_context)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "nextToken" in body
    decoded_token = json.loads(base64.b64decode(body["nextToken"]))
    assert decoded_token == {"imageId": "4_last"}


def test_list_images_invalid_next_token(mock_context):
    event = {"queryStringParameters": {"nextToken": "invalid-base64"}}
    response = list_images.handler(event, mock_context)
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["message"] == "Invalid nextToken format."


def test_list_images_database_error(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.scan_items.side_effect = DatabaseError("DB scan failed")
    event = {"queryStringParameters": None}
    response = list_images.handler(event, mock_context)
    assert response["statusCode"] == 500
    assert json.loads(response["body"])["message"] == "A service error occurred."

def test_list_images_success_query_tags(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.query_by_tag.return_value = ([{"imageId": "4", "tags": "cat,cute"}], None)
    event = {"queryStringParameters": {"tags": "cat"}}
    response = list_images.handler(event, mock_context)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body["items"]) == 1
    assert body["items"][0]["imageId"] == "4"
    mock_dynamodb_service.query_by_tag.assert_called_once_with("cat", None)


def test_get_image_success(mock_services, mock_context):
    mock_s3_service, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.return_value = {"imageId": "imgid", "s3_key": "s3key"}
    mock_s3_service.get_file_url.return_value = "http://mock-s3-url.com/s3key"
    event = {"pathParameters": {"imageId": "imgid"}}
    response = get_image.handler(event, mock_context)
    assert response["statusCode"] == 302
    assert response["headers"]["Location"] == "http://mock-s3-url.com/s3key"
    mock_dynamodb_service.get_item.assert_called_once_with("imgid")
    mock_s3_service.get_file_url.assert_called_once_with("s3key")


def test_get_image_not_found(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.side_effect = ImageNotFoundError("Image not found")
    event = {"pathParameters": {"imageId": "nonexistent"}}
    response = get_image.handler(event, mock_context)
    assert response["statusCode"] == 404
    assert json.loads(response["body"])["message"] == "Image not found"


def test_get_image_s3_error(mock_services, mock_context):
    mock_s3_service, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.return_value = {"imageId": "imgid", "s3_key": "s3key"}
    mock_s3_service.get_file_url.side_effect = S3Error("S3 URL failed")
    event = {"pathParameters": {"imageId": "imgid"}}
    response = get_image.handler(event, mock_context)
    assert response["statusCode"] == 500
    assert json.loads(response["body"])["message"] == "A service error occurred."


def test_delete_image_success(mock_services, mock_context):
    mock_s3_service, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.return_value = {"imageId": "delid", "s3_key": "dels3key"}
    event = {"pathParameters": {"imageId": "delid"}}
    response = delete_image.handler(event, mock_context)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["message"] == "Image deleted successfully"
    mock_dynamodb_service.get_item.assert_called_once_with("delid")
    mock_s3_service.delete_file.assert_called_once_with("dels3key")
    mock_dynamodb_service.delete_item.assert_called_once_with("delid")


def test_delete_image_not_found(mock_services, mock_context):
    _, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.side_effect = ImageNotFoundError("Image not found")
    event = {"pathParameters": {"imageId": "nonexistent"}}
    response = delete_image.handler(event, mock_context)
    assert response["statusCode"] == 404
    assert json.loads(response["body"])["message"] == "Image not found"


def test_delete_image_s3_error(mock_services, mock_context):
    mock_s3_service, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.return_value = {"imageId": "delid", "s3_key": "dels3key"}
    mock_s3_service.delete_file.side_effect = S3Error("S3 delete failed")
    event = {"pathParameters": {"imageId": "delid"}}
    response = delete_image.handler(event, mock_context)
    assert response["statusCode"] == 500
    assert json.loads(response["body"])["message"] == "A service error occurred."


def test_delete_image_database_error(mock_services, mock_context):
    mock_s3_service, mock_dynamodb_service = mock_services
    mock_dynamodb_service.get_item.return_value = {"imageId": "delid", "s3_key": "dels3key"}
    mock_dynamodb_service.delete_item.side_effect = DatabaseError("DB delete failed")
    event = {"pathParameters": {"imageId": "delid"}}
    response = delete_image.handler(event, mock_context)
    assert response["statusCode"] == 500
    assert json.loads(response["body"])["message"] == "A service error occurred."