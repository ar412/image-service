import os


class Config:
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    S3_ENDPOINT_URL = None
    DYNAMODB_ENDPOINT_URL = None
    BOTO3_CREDENTIALS = {}


class LocalConfig(Config):
    def __init__(self):
        super().__init__()
        localstack_hostname = os.environ.get("LOCALSTACK_HOSTNAME", "localhost")
        endpoint_url = f"http://{localstack_hostname}:4566"
        self.S3_ENDPOINT_URL = endpoint_url
        self.DYNAMODB_ENDPOINT_URL = endpoint_url
        self.BOTO3_CREDENTIALS = {
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
        }


class StagingConfig(Config):
    pass


class ProductionConfig(Config):
    pass


def get_config():
    env = os.environ.get("APP_ENV", "prod").lower()
    if env == "local":
        return LocalConfig()
    if env == "stage":
        return StagingConfig()
    return ProductionConfig()


config = get_config()