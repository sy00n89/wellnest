"""Run the Lambda handlers as an ordinary web server.

API Gateway's job is small: turn an HTTP request into an "event" dictionary,
call the right handler's lambda_handler(event, context), and turn the returned
dictionary back into an HTTP response. This file does the same thing, so the
handlers run unchanged on any machine.

Run with:  uvicorn server:app --host 0.0.0.0 --port 8080
"""
import os
import sys

from antithesis.assertions import reachable
from fastapi import FastAPI, Request, Response

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'handlers'))

import entries  # noqa: E402
import insights  # noqa: E402
import patterns  # noqa: E402
import plant  # noqa: E402

# First part of the URL path -> which handler serves it (same as template.yaml).
ROUTES = {
    'entries': entries,
    'plant': plant,
    'patterns': patterns,
    'insights': insights,
}

app = FastAPI()


async def to_event(request: Request) -> dict:
    """Build the event dictionary API Gateway would have sent."""
    parts = request.url.path.strip('/').split('/')
    body = (await request.body()).decode() or None

    # template.yaml defines one path parameter: /entries/{id}
    path_parameters = {'id': parts[1]} if len(parts) == 2 else None

    return {
        'httpMethod': request.method,
        'path': request.url.path,
        'pathParameters': path_parameters,
        # API Gateway sends None, not {}, when there is no query string.
        'queryStringParameters': dict(request.query_params) or None,
        'body': body,
    }


@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
async def dispatch(request: Request):
    resource = request.url.path.strip('/').split('/')[0]
    handler = ROUTES.get(resource)
    if handler is None:
        return Response(status_code=404, content='{"error": "Not found"}', media_type='application/json')

    # Bootstrap property: proves the Antithesis SDK and assertion cataloging work.
    reachable("api dispatched a request to a handler", {"resource": resource})

    result = handler.lambda_handler(await to_event(request), None)

    return Response(
        status_code=result['statusCode'],
        content=result.get('body', ''),
        headers=result.get('headers', {}),
        media_type='application/json',
    )
