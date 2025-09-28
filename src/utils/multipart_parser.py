import base64
from io import BytesIO
from werkzeug.datastructures import FileStorage
from werkzeug.http import parse_options_header
from werkzeug import formparser
from src.exceptions import InvalidRequestError


def parse_multipart(event):
    headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
    content_type = headers.get('content-type', '')
    if not content_type:
        raise InvalidRequestError("Missing 'content-type' header")

    _, options = parse_options_header(content_type)
    boundary = options.get('boundary', '').encode('utf-8')
    if not boundary:
        raise InvalidRequestError("Missing 'boundary' in 'content-type' header")
    body = base64.b64decode(event['body'])

    _stream, form, files = formparser.parse_form_data(
        environ={
            'wsgi.input': BytesIO(body),
            'CONTENT_LENGTH': str(len(body)),
            'CONTENT_TYPE': content_type
        }
    )
    return form, files
