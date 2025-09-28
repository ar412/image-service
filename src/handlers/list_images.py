import base64
import binascii
import json
import logging
from src.handlers.common import create_response, DecimalEncoder
from src.exceptions import DatabaseError, ImageNotFoundError, InvalidRequestError
from src.handlers.decorators import inject_services

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@inject_services(dynamodb=True)
def handler(event, context, dynamodb_service=None):
    try:
        query_params = event.get('queryStringParameters') or {}
        exclusive_start_key = None

        if 'nextToken' in query_params:
            try:
                exclusive_start_key = json.loads(base64.b64decode(query_params['nextToken']))
            except (TypeError, json.JSONDecodeError, binascii.Error) as e:
                return create_response(400, {"message": "Invalid nextToken format."})

        if 'imageId' in query_params:
            item = dynamodb_service.get_item(query_params['imageId'])
            items = [item] if item else []
            last_evaluated_key = None

        elif 'contentType' in query_params:
            items, last_evaluated_key = dynamodb_service.query_by_content_type(
                query_params['contentType'], exclusive_start_key
            )

        elif 'tags' in query_params:
            items, last_evaluated_key = dynamodb_service.query_by_tag(
                query_params['tags'], exclusive_start_key
            )

        else:
            items, last_evaluated_key = dynamodb_service.scan_items(exclusive_start_key)

        response_body = {"items": items}
        if last_evaluated_key:
            response_body['nextToken'] = base64.b64encode(json.dumps(last_evaluated_key, cls=DecimalEncoder).encode('utf-8')).decode('utf-8')

        return create_response(200, response_body)

    except ImageNotFoundError as e:
        logger.warning(f"Image not found when listing: {e}")
        return create_response(404, {"message": str(e)})
    except (DatabaseError, InvalidRequestError) as e:
        logger.error(f"Service error listing images: {e}")
        return create_response(500, {"message": "A service error occurred."})
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        return create_response(500, {"message": "Internal server error"})
