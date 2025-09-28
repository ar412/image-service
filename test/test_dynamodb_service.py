import pytest
import os
from unittest.mock import MagicMock
from botocore.exceptions import ClientError
from src.services.dynamodb_service import DynamoDBService
from src.exceptions import DatabaseError, ImageNotFoundError

@pytest.fixture
def dynamodb_service_instance(mocked_dynamodb):
    service = DynamoDBService(dynamodb_resource=mocked_dynamodb)
    service.table = mocked_dynamodb.Table(service.table_name)
    return service


def test_dynamodb_service_init_no_table_name():
    if "METADATA_TABLE_NAME" in os.environ:
        del os.environ["METADATA_TABLE_NAME"]
    with pytest.raises(ValueError, match="METADATA_TABLE_NAME environment variable not set."):
        DynamoDBService(dynamodb_resource=MagicMock())


def test_put_item_success(dynamodb_service_instance):
    item = {"imageId": "123", "filename": "test.jpg"}
    dynamodb_service_instance.put_item(item)
    response = dynamodb_service_instance.table.get_item(Key={"imageId": "123"})
    assert response["Item"] == item


def test_put_item_dynamodb_error(dynamodb_service_instance):
    dynamodb_service_instance.table.put_item = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "DB error"}}, "PutItem")
    )
    with pytest.raises(DatabaseError, match="Failed to put item"):
        dynamodb_service_instance.put_item({"imageId": "fail"})


def test_get_item_success(dynamodb_service_instance):
    item = {"imageId": "456", "filename": "another.png"}
    dynamodb_service_instance.table.put_item(Item=item)
    retrieved_item = dynamodb_service_instance.get_item("456")
    assert retrieved_item == item


def test_get_item_not_found(dynamodb_service_instance):
    with pytest.raises(ImageNotFoundError, match="Image with ID 'non-existent' not found."):
        dynamodb_service_instance.get_item("non-existent")


def test_get_item_dynamodb_error(dynamodb_service_instance):
    dynamodb_service_instance.table.get_item = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "DB error"}}, "GetItem")
    )
    with pytest.raises(DatabaseError, match="Failed to get item"):
        dynamodb_service_instance.get_item("fail")


def test_delete_item_success(dynamodb_service_instance):
    item = {"imageId": "789", "filename": "delete.gif"}
    dynamodb_service_instance.table.put_item(Item=item)
    dynamodb_service_instance.delete_item("789")
    response = dynamodb_service_instance.table.get_item(Key={"imageId": "789"})
    assert "Item" not in response


def test_delete_item_dynamodb_error(dynamodb_service_instance):
    dynamodb_service_instance.table.delete_item = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "DB error"}}, "DeleteItem")
    )
    with pytest.raises(DatabaseError, match="Failed to delete item"):
        dynamodb_service_instance.delete_item("fail")


def test_query_by_content_type_success(dynamodb_service_instance):
    item1 = {"imageId": "img1", "contentType": "image/jpeg", "filename": "1.jpg"}
    item2 = {"imageId": "img2", "contentType": "image/jpeg", "filename": "2.jpg"}
    item3 = {"imageId": "img3", "contentType": "image/png", "filename": "3.png"}
    dynamodb_service_instance.table.put_item(Item=item1)
    dynamodb_service_instance.table.put_item(Item=item2)
    dynamodb_service_instance.table.put_item(Item=item3)

    items, last_key = dynamodb_service_instance.query_by_content_type("image/jpeg")
    assert len(items) == 2
    assert any(i["imageId"] == "img1" for i in items)
    assert any(i["imageId"] == "img2" for i in items)
    assert last_key is None


def test_query_by_content_type_pagination(dynamodb_service_instance):
    for i in range(5):
        dynamodb_service_instance.table.put_item(
            Item={"imageId": f"img{i}", "contentType": "image/gif", "filename": f"{i}.gif"}
        )
    dynamodb_service_instance.table.query = MagicMock(
        side_effect=[
            {"Items": [{"imageId": "img0"}, {"imageId": "img1"}], "LastEvaluatedKey": {"imageId": "img1"}},
            {"Items": [{"imageId": "img2"}, {"imageId": "img3"}], "LastEvaluatedKey": {"imageId": "img3"}},
            {"Items": [{"imageId": "img4"}], "LastEvaluatedKey": None},
        ]
    )
    items1, last_key1 = dynamodb_service_instance.query_by_content_type("image/gif")
    assert len(items1) == 2
    assert last_key1 == {"imageId": "img1"}

    items2, last_key2 = dynamodb_service_instance.query_by_content_type("image/gif", last_key1)
    assert len(items2) == 2
    assert last_key2 == {"imageId": "img3"}


def test_query_by_content_type_dynamodb_error(dynamodb_service_instance):
    dynamodb_service_instance.table.query = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "DB error"}}, "Query")
    )
    with pytest.raises(DatabaseError, match="Failed to query by contentType"):
        dynamodb_service_instance.query_by_content_type("image/jpeg")


def test_scan_items_success(dynamodb_service_instance):
    item1 = {"imageId": "scan1", "contentType": "image/jpeg"}
    item2 = {"imageId": "scan2", "contentType": "image/png"}
    dynamodb_service_instance.table.put_item(Item=item1)
    dynamodb_service_instance.table.put_item(Item=item2)

    items, last_key = dynamodb_service_instance.scan_items()
    assert len(items) == 2
    assert last_key is None


def test_scan_items_dynamodb_error(dynamodb_service_instance):
    dynamodb_service_instance.table.scan = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "DB error"}}, "Scan")
    )
    with pytest.raises(DatabaseError, match="Failed to scan table"):
        dynamodb_service_instance.scan_items()

def test_query_by_tag_dynamodb_error(dynamodb_service_instance):
    dynamodb_service_instance.table.scan = MagicMock(
        side_effect=ClientError({"Error": {"Code": "500", "Message": "DB error"}}, "Scan")
    )
    with pytest.raises(DatabaseError, match="Failed to query by tag"):
        dynamodb_service_instance.query_by_tag("test-tag")