"""Shared test setup: point the handlers at local DynamoDB and start each test empty."""
import json
import os
import sys

import boto3
import pytest

# These must be set before the handlers are imported, because the handlers
# read them at import time. Tests use their own tables, which get wiped before
# every test, so running tests never deletes your local dev data.
os.environ.setdefault('DYNAMODB_ENDPOINT', 'http://localhost:8001')
os.environ['ENTRIES_TABLE'] = 'test-entries'
os.environ['PLANT_TABLE'] = 'test-plant'
os.environ['PATTERNS_TABLE'] = 'test-patterns'
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'local')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'local')

BACKEND = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, 'handlers'))

import create_tables  # noqa: E402


@pytest.fixture(autouse=True)
def empty_tables():
    """Runs before every test: make sure the tables exist and are empty."""
    create_tables.main()
    client = boto3.client('dynamodb', endpoint_url=os.environ['DYNAMODB_ENDPOINT'])
    for spec in create_tables.TABLES:
        key_names = [k['AttributeName'] for k in spec['KeySchema']]
        for item in client.scan(TableName=spec['TableName'])['Items']:
            client.delete_item(TableName=spec['TableName'], Key={k: item[k] for k in key_names})


def call(handler, method, body=None, path_id=None, query=None):
    """Call a handler the way API Gateway would, and decode the JSON reply."""
    event = {
        'httpMethod': method,
        'body': json.dumps(body) if body is not None else None,
        'pathParameters': {'id': path_id} if path_id else None,
        'queryStringParameters': query,
    }
    result = handler.lambda_handler(event, None)
    return result['statusCode'], json.loads(result['body']) if result['body'] else None
