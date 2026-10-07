"""Trigger counts (the patterns table), shared by the entries and patterns handlers.

Counts only change through DynamoDB's atomic ADD, so concurrent updates are
never lost and +1/-1 can arrive in any order and still add up. Severity is kept
as a running total (severity_total) so the average can be computed on read.
A row whose frequency reaches zero is removed; a row may briefly hold a
negative frequency when a delete's -1 arrives before its check-in's +1, and
reads skip it.
"""
import os
from decimal import Decimal

import boto3

dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('DYNAMODB_ENDPOINT'))
table = dynamodb.Table(os.environ['PATTERNS_TABLE'])


def adjust(user_id, triggers, stress_level, direction):
    """Add (direction=+1) or remove (direction=-1) one check-in's triggers."""
    stress = Decimal(str(stress_level))
    for trigger in triggers:
        key = {'user_id': user_id, 'trigger': trigger}
        result = table.update_item(
            Key=key,
            UpdateExpression='ADD frequency :n, severity_total :s',
            ExpressionAttributeValues={':n': Decimal(direction), ':s': stress * direction},
            ReturnValues='UPDATED_NEW',
        )
        if result['Attributes']['frequency'] == 0:
            try:
                table.delete_item(
                    Key=key,
                    ConditionExpression='frequency = :zero',
                    ExpressionAttributeValues={':zero': Decimal(0)},
                )
            except table.meta.client.exceptions.ConditionalCheckFailedException:
                pass  # another update changed it first; leave it


def to_response(row):
    """Shape a stored row for the API: frequency and average severity."""
    frequency = row.get('frequency', 0)
    if 'severity_total' in row and frequency:
        severity = round(float(row['severity_total']) / float(frequency), 1)
    else:  # rows written before severity_total existed store the average directly
        severity = float(row.get('severity', 0))
    return {'user_id': row['user_id'], 'trigger': row['trigger'],
            'frequency': frequency, 'severity': severity}
