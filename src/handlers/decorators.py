from functools import wraps
from src.services.s3_service import S3Service
from src.services.dynamodb_service import DynamoDBService

_s3_service = None
_dynamodb_service = None


def inject_services(s3=False, dynamodb=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global _s3_service, _dynamodb_service
            if s3 and _s3_service is None: _s3_service = S3Service()
            if dynamodb and _dynamodb_service is None: _dynamodb_service = DynamoDBService()

            if s3:
                kwargs['s3_service'] = _s3_service
            if dynamodb:
                kwargs['dynamodb_service'] = _dynamodb_service
            return func(*args, **kwargs) # pragma: no cover
        return wrapper
    return decorator # pragma: no cover