"""Reads over a user's entries, shared by the handlers.

DynamoDB returns at most 1 MB per query page, so every read follows
LastEvaluatedKey until the last page. Deleted entries are kept as tombstones
(deleted = true, see entries.delete_entry) and are skipped here.
"""
import os

from boto3.dynamodb.conditions import Attr, Key

from aws import dynamodb

entries_table = dynamodb.Table(os.environ['ENTRIES_TABLE'])

NOT_DELETED = Attr('deleted').not_exists()


def all_entries(user_id):
    """Every entry for the user."""
    items = []
    kwargs = {'KeyConditionExpression': Key('user_id').eq(user_id), 'FilterExpression': NOT_DELETED}
    while True:
        response = entries_table.query(**kwargs)
        items.extend(response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            return items
        kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']


def count_entries(user_id):
    """How many entries the user has, without reading them."""
    total = 0
    kwargs = {'KeyConditionExpression': Key('user_id').eq(user_id), 'FilterExpression': NOT_DELETED,
              'Select': 'COUNT'}
    while True:
        response = entries_table.query(**kwargs)
        total += response['Count']
        if 'LastEvaluatedKey' not in response:
            return total
        kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
