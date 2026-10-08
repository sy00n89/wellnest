import json
from decimal import Decimal

import entry_queries
from plant_stages import plant_stage

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS'
    }

def lambda_handler(event, context):
    method = event.get('httpMethod', '')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}

    try:
        if method == 'GET':
            return get_plant(event)
        else:
            return {'statusCode': 405, 'headers': cors_headers(), 'body': json.dumps({'error': 'Method not allowed'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': str(e)})}

def get_plant(event):
    """The plant is computed from the user's entries on every read.

    Storing a count separately let it drift from the entries (concurrent
    recounts, and retried increments counted twice), so nothing is stored.
    """
    params = event.get('queryStringParameters') or {}
    user_id = params.get('user_id', 'default')

    check_ins = entry_queries.count_entries(user_id)
    item = {'user_id': user_id, 'check_ins': check_ins, 'stage': plant_stage(check_ins)}

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps(item, cls=DecimalEncoder)
    }
