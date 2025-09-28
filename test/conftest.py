import pytest
import os
from moto import mock_aws
import boto3
from unittest.mock import patch

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="function")
def set_env_vars():
    """Set common environment variables for Lambda functions."""
    os.environ["IMAGE_BUCKET_NAME"] = "test-image-bucket"
    os.environ["METADATA_TABLE_NAME"] = "test-metadata-table"
    os.environ["APP_ENV"] = "prod" # Default to prod for most tests
    yield
    del os.environ["IMAGE_BUCKET_NAME"]
    del os.environ["METADATA_TABLE_NAME"]
    del os.environ["APP_ENV"]
    if "LOCALSTACK_HOSTNAME" in os.environ:
        del os.environ["LOCALSTACK_HOSTNAME"]

@pytest.fixture(scope="function")
def set_localstack_env_vars(set_env_vars):
    """Set environment variables for LocalStack specific tests."""
    os.environ["LOCALSTACK_HOSTNAME"] = "localstack-main" # Use a non-localhost name
    os.environ["APP_ENV"] = "local"
    yield

@pytest.fixture(scope="function")
def mocked_s3(aws_credentials, set_env_vars):
    """Mocked S3 client and bucket."""
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=os.environ["IMAGE_BUCKET_NAME"])
        yield conn

@pytest.fixture(scope="function")
def mocked_dynamodb(aws_credentials, set_env_vars):
    """Mocked DynamoDB client and table."""
    with mock_aws():
        conn = boto3.resource("dynamodb", region_name="us-east-1")
        conn.create_table(
            TableName=os.environ["METADATA_TABLE_NAME"],
            KeySchema=[{"AttributeName": "imageId", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "imageId", "AttributeType": "S"},
                {"AttributeName": "contentType", "AttributeType": "S"},
                {"AttributeName": "tags", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "ContentTypeIndex",
                    "KeySchema": [{"AttributeName": "contentType", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "TagsIndex",
                    "KeySchema": [
                        {"AttributeName": "tags", "KeyType": "HASH"},
                        {"AttributeName": "imageId", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
        yield conn