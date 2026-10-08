"""Shared DynamoDB connection and error handling for the handlers.

Option B (owner decision 2026-10-08): fail fast. API Gateway cuts requests off
at 29 s, so a slow or unreachable DynamoDB must produce a clear "try again"
answer in time rather than a correct answer too late. Each call gives up after
2 s to connect or 4 s to read, with at most 2 attempts.
"""
import json
import os

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)

FAIL_FAST = Config(connect_timeout=2, read_timeout=4,
                   retries={'mode': 'standard', 'total_max_attempts': 2})

dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('DYNAMODB_ENDPOINT'), config=FAIL_FAST)

UNAVAILABLE = (ConnectionClosedError, ConnectTimeoutError, EndpointConnectionError, ReadTimeoutError)


def error_response(e, headers):
    """503 when DynamoDB could not be reached in time, 500 for anything else."""
    if isinstance(e, UNAVAILABLE):
        print(f'DynamoDB unavailable: {type(e).__name__}: {e}')
        return {'statusCode': 503, 'headers': {**headers, 'Retry-After': '5'},
                'body': json.dumps({'error': 'temporarily unavailable, please try again'})}
    return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}
