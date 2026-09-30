"""Create the Wellnest DynamoDB tables in a local DynamoDB.

Mirrors the table definitions in template.yaml. Safe to run more than once:
tables that already exist are skipped.
"""
import os

import boto3

TABLES = [
    {
        'TableName': os.environ.get('ENTRIES_TABLE', 'wellnest-entries'),
        'KeySchema': [
            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'},
        ],
    },
    {
        'TableName': os.environ.get('PLANT_TABLE', 'wellnest-plant'),
        'KeySchema': [
            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
        ],
    },
    {
        'TableName': os.environ.get('PATTERNS_TABLE', 'wellnest-patterns'),
        'KeySchema': [
            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
            {'AttributeName': 'trigger', 'KeyType': 'RANGE'},
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'trigger', 'AttributeType': 'S'},
        ],
    },
]


def main():
    endpoint = os.environ.get('DYNAMODB_ENDPOINT')
    if not endpoint:
        raise SystemExit('DYNAMODB_ENDPOINT is not set; refusing to create tables in real AWS.')

    client = boto3.client('dynamodb', endpoint_url=endpoint)
    existing = client.list_tables()['TableNames']

    for spec in TABLES:
        name = spec['TableName']
        if name in existing:
            print(f'exists:  {name}')
            continue
        client.create_table(BillingMode='PAY_PER_REQUEST', **spec)
        print(f'created: {name}')


if __name__ == '__main__':
    main()
