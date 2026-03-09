import json
import os
import uuid
import time
from decimal import Decimal
from datetime import datetime, timezone
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
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
        'timestamp': Decimal(str(int(now * 1000))),
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

    table.put_item(Item=item)

    # Update plant after entry
    update_plant(user_id)

    return {
        'statusCode': 201,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Entry created', 'id': entry_id})
    }

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

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Entry deleted'})
    }

def update_plant(user_id):
    """Update plant stage based on total entries"""
    try:
        plant_table = dynamodb.Table(os.environ['PLANT_TABLE'])

        # Count total entries
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        total = len(response.get('Items', []))

        # Determine stage
        if total >= 20:
            stage = 'mature_tree'
        elif total >= 14:
            stage = 'young_tree'
        elif total >= 8:
            stage = 'plant'
        elif total >= 3:
            stage = 'seedling'
        else:
            stage = 'sprout'

        plant_table.put_item(Item={
            'user_id': user_id,
            'stage': stage,
            'check_ins': Decimal(str(total)),
        })
    except Exception as e:
        print(f"Plant update error: {e}")