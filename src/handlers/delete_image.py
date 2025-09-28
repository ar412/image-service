import logging
from src.handlers.common import create_response
from src.exceptions import ImageNotFoundError, S3Error, DatabaseError
from src.handlers.decorators import inject_services

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@inject_services(s3=True, dynamodb=True)
def handler(event, context, s3_service=None, dynamodb_service=None):
    try:
        image_id = event['pathParameters']['imageId']
        metadata = dynamodb_service.get_item(image_id)
        s3_service.delete_file(metadata['s3_key'])
        dynamodb_service.delete_item(image_id)
        return create_response(200, {"message": "Image deleted successfully"})

    except ImageNotFoundError as e:
        logger.warning(f"Attempted to delete non-existent image ID '{image_id}': {e}")
        return create_response(404, {"message": str(e)})
    except (S3Error, DatabaseError) as e:
        logger.error(f"Service error deleting image {image_id}: {e}")
        return create_response(500, {"message": "A service error occurred."})
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        return create_response(500, {"message": "Internal server error"})
