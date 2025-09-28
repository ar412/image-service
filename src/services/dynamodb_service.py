import boto3
import os
import logging
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from src.config import config
from src.exceptions import DatabaseError, ImageNotFoundError

logger = logging.getLogger(__name__)
 
 
class DynamoDBService:
    def __init__(self, dynamodb_resource=None): # pragma: no cover
        self.table_name = os.environ.get("METADATA_TABLE_NAME")
        if not self.table_name:
            raise ValueError("METADATA_TABLE_NAME environment variable not set.")

        if dynamodb_resource:
            self.dynamodb_resource = dynamodb_resource
        else:
            boto_kwargs = {
                "region_name": config.AWS_REGION,
                **config.BOTO3_CREDENTIALS
            }
            if config.DYNAMODB_ENDPOINT_URL:
                boto_kwargs["endpoint_url"] = config.DYNAMODB_ENDPOINT_URL
                logger.debug(f"Using DynamoDB endpoint: {config.DYNAMODB_ENDPOINT_URL}")

            self.dynamodb_resource = boto3.resource("dynamodb", **boto_kwargs)
        self.table = self.dynamodb_resource.Table(self.table_name)

    def put_item(self, item):
        try:
            return self.table.put_item(Item=item)
        except ClientError as e:
            raise DatabaseError(f"Failed to put item in DynamoDB: {e}") from e

    def get_item(self, image_id):
        try:
            response = self.table.get_item(Key={'imageId': image_id})
            item = response.get('Item')
            if not item:
                raise ImageNotFoundError(f"Image with ID '{image_id}' not found.")
            return item # pragma: no cover
        except ClientError as e:
            raise DatabaseError(f"Failed to get item '{image_id}' from DynamoDB: {e}") from e

    def delete_item(self, image_id):
        try:
            return self.table.delete_item(Key={'imageId': image_id})
        except ClientError as e:
            raise DatabaseError(f"Failed to delete item '{image_id}' from DynamoDB: {e}") from e

    def query_by_content_type(self, content_type, exclusive_start_key=None):
        query_kwargs = {
            'IndexName': 'ContentTypeIndex',
            'KeyConditionExpression': Key('contentType').eq(content_type)
        }
        if exclusive_start_key:
            query_kwargs['ExclusiveStartKey'] = exclusive_start_key

        try:
            response = self.table.query(**query_kwargs)
            return response.get('Items', []), response.get('LastEvaluatedKey') # pragma: no cover
        except ClientError as e:
            raise DatabaseError(f"Failed to query by contentType '{content_type}': {e}") from e

    def query_by_tag(self, tag, exclusive_start_key=None):
        scan_kwargs = {
            'FilterExpression': Attr('tags').contains(tag)
        }
        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = exclusive_start_key

        try:
            response = self.table.scan(**scan_kwargs)
            return response.get('Items', []), response.get('LastEvaluatedKey') # pragma: no cover
        except ClientError as e:
            raise DatabaseError(f"Failed to query by tag '{tag}': {e}") from e

    def scan_items(self, exclusive_start_key: dict = None):
        scan_kwargs = {}
        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = exclusive_start_key

        try:
            response = self.table.scan(**scan_kwargs)
            return response.get('Items', []), response.get('LastEvaluatedKey') # pragma: no cover
        except ClientError as e:
            raise DatabaseError(f"Failed to scan table: {e}") from e
