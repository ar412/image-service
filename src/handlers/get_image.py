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
        download_url = s3_service.get_file_url(metadata['s3_key'])
        return create_response(302, None, headers={"Location": download_url})

    except ImageNotFoundError as e:
        logger.warning(f"Image not found for ID '{image_id}': {e}")
        return create_response(404, {"message": str(e)})
    except (S3Error, DatabaseError) as e:
        logger.error(f"Service error getting image {image_id}: {e}")
        return create_response(500, {"message": "A service error occurred."})
    except Exception as e:
        logger.error(f"Error getting image: {e}")
        return create_response(500, {"message": "Internal server error"})
