import json
import os
from decimal import Decimal
import boto3

import pattern_counts
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('DYNAMODB_ENDPOINT'))
table = dynamodb.Table(os.environ['PATTERNS_TABLE'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

def lambda_handler(event, context):
    method = event.get('httpMethod', '')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}

    try:
        if method == 'GET':
            return get_patterns(event)
        elif method == 'POST':
            return upsert_pattern(event)
        else:
            return {'statusCode': 405, 'headers': cors_headers(), 'body': json.dumps({'error': 'Method not allowed'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': str(e)})}

def get_patterns(event):
    params = event.get('queryStringParameters') or {}
    user_id = params.get('user_id', 'default')

    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )

    patterns = [pattern_counts.to_response(p) for p in response.get('Items', [])
                if p.get('frequency', 0) > 0]
    patterns.sort(key=lambda x: x['frequency'], reverse=True)

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps(patterns, cls=DecimalEncoder)
    }

def upsert_pattern(event):
    body = json.loads(event.get('body', '{}'))
    user_id = body.get('user_id', 'default')
    trigger = body.get('trigger', '')
    stress_level = body.get('stress_level', 5)

    if not trigger:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Missing trigger'})}

    pattern_counts.adjust(user_id, [trigger], stress_level, +1)

    return {
        'statusCode': 201,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Pattern updated'})
    }
