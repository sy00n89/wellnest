import json
import os
import uuid
import time
from decimal import Decimal
from datetime import datetime, timezone
import boto3
from antithesis.assertions import unreachable
from boto3.dynamodb.conditions import Key

import pattern_counts

dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('DYNAMODB_ENDPOINT'))
table = dynamodb.Table(os.environ['ENTRIES_TABLE'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS'
    }

def lambda_handler(event, context):
    method = event.get('httpMethod', '')
    path = event.get('path', '')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}

    try:
        if method == 'GET':
            return get_entries(event)
        elif method == 'POST':
            return create_entry(event)
        elif method == 'DELETE':
            return delete_entry(event)
        else:
            return {'statusCode': 405, 'headers': cors_headers(), 'body': json.dumps({'error': 'Method not allowed'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': str(e)})}

def get_entries(event):
    params = event.get('queryStringParameters') or {}
    user_id = params.get('user_id', 'default')

    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )

    entries = response.get('Items', [])
    entries.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps(entries, cls=DecimalEncoder)
    }

def create_entry(event):
    body = json.loads(event.get('body', '{}'))

    user_id = body.get('user_id', 'default')
    now = time.time()
    entry_id = str(uuid.uuid4())

    # Use date/time sent from frontend (local timezone) instead of server UTC
    date = body.get('date') or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    entry_time = body.get('time') or datetime.now(timezone.utc).strftime('%H:%M:%S')

    item = {
        'user_id': user_id,
        'timestamp': Decimal(str(int(now * 1000))),  # may move forward, see put_new_entry
        'id': entry_id,
        'date': date,
        'time': entry_time,
        'mood': body.get('mood', 'neutral'),
        'stress_level': Decimal(str(body.get('stress_level', 5))),
        'triggers': body.get('triggers', []),
        'physical_signs': body.get('physical_signs', []),
        'notes': body.get('notes', ''),
        'appraisal_type': body.get('appraisal_type', ''),
        'perceived_resources': body.get('perceived_resources', []),
        'appraisal_reflection': body.get('appraisal_reflection', ''),
        'vulnerability_factors': body.get('vulnerability_factors', {}),
    }

    put_new_entry(item)

    # Update plant and trigger counts after entry
    update_plant(user_id)
    update_trigger_counts(user_id, item, +1)

    return {
        'statusCode': 201,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Entry created', 'id': entry_id})
    }

def put_new_entry(item, max_attempts=100):
    """Save a new entry without overwriting another one.

    The key is (user_id, timestamp in ms), so two check-ins in the same
    millisecond would collide. Only write if the key is free; if it is taken,
    move forward one millisecond and try again.
    """
    for _ in range(max_attempts):
        try:
            table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(#ts)',
                ExpressionAttributeNames={'#ts': 'timestamp'},
            )
            return
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            # boto3 retries a put whose reply was lost; if the slot already
            # holds this very entry, that earlier attempt succeeded.
            existing = table.get_item(
                Key={'user_id': item['user_id'], 'timestamp': item['timestamp']}
            ).get('Item')
            if existing and existing.get('id') == item['id']:
                return
            item['timestamp'] += 1
    raise RuntimeError('could not find a free timestamp for the new entry')

def delete_entry(event):
    params = event.get('queryStringParameters') or {}
    user_id = params.get('user_id', 'default')
    path_params = event.get('pathParameters') or {}
    entry_id = path_params.get('id')

    if not entry_id:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Missing entry id'})}

    # Find the entry by id to get its timestamp
    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )
    entries = response.get('Items', [])
    entry = next((e for e in entries if e.get('id') == entry_id), None)

    if not entry:
        return {'statusCode': 404, 'headers': cors_headers(), 'body': json.dumps({'error': 'Entry not found'})}

    table.delete_item(
        Key={'user_id': user_id, 'timestamp': entry['timestamp']}
    )

    # Update plant and trigger counts after delete
    update_plant(user_id)
    update_trigger_counts(user_id, entry, -1)

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Entry deleted'})
    }

def update_trigger_counts(user_id, entry, direction):
    """Count (+1) or uncount (-1) an entry's triggers in the patterns table."""
    try:
        pattern_counts.adjust(user_id, entry.get('triggers', []),
                              entry.get('stress_level', 5), direction)
    except Exception as e:
        print(f"Trigger count update error: {e}")
        unreachable("trigger counts failed to update after an entry change", {'error': type(e).__name__})

# Every 20 check-ins grows the plant one stage. Keep in sync with
# STAGE_THRESHOLDS in src/App.jsx.
PLANT_STAGE_THRESHOLDS = [
    (80, 'mature_tree'),
    (60, 'young_tree'),
    (40, 'plant'),
    (20, 'seedling'),
]

def plant_stage(total):
    """Return the plant stage for a number of check-ins."""
    for threshold, stage in PLANT_STAGE_THRESHOLDS:
        if total >= threshold:
            return stage
    return 'sprout'

def update_plant(user_id):
    """Update plant stage based on total entries"""
    try:
        plant_table = dynamodb.Table(os.environ['PLANT_TABLE'])

        # Count total entries
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        total = len(response.get('Items', []))

        plant_table.put_item(Item={
            'user_id': user_id,
            'stage': plant_stage(total),
            'check_ins': Decimal(str(total)),
        })
    except Exception as e:
        print(f"Plant update error: {e}")
        unreachable("plant failed to update after an entry change", {'error': type(e).__name__})
