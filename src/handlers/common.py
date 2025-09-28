import json
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            if o % 1 == 0:
                return int(o)
            return float(o)
        return super(DecimalEncoder, self).default(o)

def create_response(status_code, body, headers=None):
    if headers is None:
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        }
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, cls=DecimalEncoder) if body is not None else ""
    }
