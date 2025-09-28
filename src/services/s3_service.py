import boto3
import os
from src.config import config
from botocore.exceptions import ClientError
from src.exceptions import S3Error


class S3Service:
    def __init__(self, s3_client=None): # pragma: no cover
        if s3_client:
            self.s3_client = s3_client
        else:
            boto_kwargs = {
                "region_name": config.AWS_REGION,
                **config.BOTO3_CREDENTIALS
            }
            if config.S3_ENDPOINT_URL:
                boto_kwargs["endpoint_url"] = config.S3_ENDPOINT_URL

            self.s3_client = boto3.client("s3", **boto_kwargs)
        self.bucket_name = os.environ.get("IMAGE_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("IMAGE_BUCKET_NAME environment variable not set.")

    def upload_file(self, file_bytes, object_name, content_type):
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file_bytes,
                ContentType=content_type
            )
            return object_name
        except ClientError as e:
            raise S3Error(f"Failed to upload {object_name} to S3: {e}") from e
    
    def get_file_url(self, object_name):
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object', Params={'Bucket': self.bucket_name, 'Key': object_name}, ExpiresIn=3600
            )
        except ClientError as e:
            raise S3Error(f"Failed to generate URL for {object_name}: {e}") from e
        
        localstack_hostname = os.environ.get("LOCALSTACK_HOSTNAME")
        if localstack_hostname:
            url = url.replace(localstack_hostname, "localhost")

        return url

    def delete_file(self, object_name):
        try:
            return self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
        except ClientError as e:
            raise S3Error(f"Failed to delete {object_name} from S3: {e}") from e
