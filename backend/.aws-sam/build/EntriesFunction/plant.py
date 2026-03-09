import json
import os
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['PLANT_TABLE'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS'
    }

def lambda_handler(event, context):
    method = event.get('httpMethod', '')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}

    try:
        if method == 'GET':
            return get_plant(event)
        elif method == 'POST' or method == 'PUT':
            return update_plant(event)
        else:
            return {'statusCode': 405, 'headers': cors_headers(), 'body': json.dumps({'error': 'Method not allowed'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': str(e)})}

def get_plant(event):
    params = event.get('queryStringParameters') or {}
    user_id = params.get('user_id', 'default')

    response = table.get_item(Key={'user_id': user_id})
    item = response.get('Item')

    if not item:
        # Return default plant
        item = {
            'user_id': user_id,
            'stage': 'sprout',
            'check_ins': 0,
            'days_active': 0,
        }

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps(item, cls=DecimalEncoder)
    }

def update_plant(event):
    body = json.loads(event.get('body', '{}'))
    user_id = body.get('user_id', 'default')

    item = {
        'user_id': user_id,
        'stage': body.get('stage', 'sprout'),
        'check_ins': Decimal(str(body.get('check_ins', 0))),
        'days_active': Decimal(str(body.get('days_active', 0))),
    }

    table.put_item(Item=item)

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Plant updated'})
    }