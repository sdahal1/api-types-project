"""Fictional public product lookup for a REST API Lambda proxy integration.

API Gateway enforces the API-key requirement before invoking this function.
The key is a usage identifier, not evidence that a shopper has signed in.
"""

import json
import re

PRODUCTS = {
    "1738": {
        "productId": "1738",
        "name": "Everyday Headphones",
        "price": 79.99,
        "currency": "USD",
    }
}


def handler(event, context):
    # REST proxy events expose pathParameters directly. An HTTP API v2 event
    # has a different overall shape; do not assume every event is identical.
    path_parameters = event.get("pathParameters") or {}
    product_id = path_parameters.get("productId", "")

    if not isinstance(product_id, str) or not re.fullmatch(r"[0-9]{1,12}", product_id):
        status, payload = 400, {"message": "productId must contain 1 to 12 digits"}
    elif product_id not in PRODUCTS:
        status, payload = 404, {"message": "Product not found"}
    else:
        status, payload = 200, PRODUCTS[product_id]

    # Correlate one gateway request with one handler result. Do not print the
    # whole event: it can contain API keys, tokens, addresses, and other data.
    print(json.dumps({
        "requestId": (event.get("requestContext") or {}).get("requestId", "local"),
        "operation": "productLookup",
        "status": status,
    }))
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, separators=(",", ":")),
    }
