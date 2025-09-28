import uuid
import logging
import time
from src.handlers.common import create_response
from src.utils.multipart_parser import parse_multipart
from src.exceptions import InvalidRequestError, S3Error, DatabaseError
from src.handlers.decorators import inject_services

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@inject_services(s3=True, dynamodb=True)
def handler(event, context, s3_service=None, dynamodb_service=None):
    try:
        form_data, files = parse_multipart(event)

        if 'file' not in files:
            return create_response(400, {"message": "File part 'file' is required."})

        image_file = files['file']
        image_id = str(uuid.uuid4())
        file_name = f"{image_id}-{image_file.filename}"

        s3_service.upload_file(image_file.read(), file_name, image_file.content_type)

        metadata = {k: v for k, v in form_data.items()}

        if 'tags' in metadata and isinstance(metadata['tags'], str):
            metadata['tags'] = [tag.strip() for tag in metadata['tags'].split(',')]

        metadata.update({
            'imageId': image_id,
            'filename': image_file.filename,
            's3_key': file_name,
            'contentType': image_file.content_type,
            'uploadTimestamp': int(time.time()),
        })

        dynamodb_service.put_item(metadata)
        
        return create_response(201, {"message": "Image uploaded successfully", "imageId": image_id})

    except InvalidRequestError as e:
        logger.warning(f"Bad request: {e}")
        return create_response(400, {"message": str(e)})
    except (S3Error, DatabaseError) as e:
        logger.error(f"Service error uploading image: {e}")
        return create_response(500, {"message": "A service error occurred."})
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return create_response(500, {"message": "Internal server error"})
