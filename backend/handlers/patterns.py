import json
from collections import defaultdict
from decimal import Decimal

import aws
import entry_queries

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
            return get_patterns(event)
        else:
            return {'statusCode': 405, 'headers': cors_headers(), 'body': json.dumps({'error': 'Method not allowed'})}
    except Exception as e:
        return aws.error_response(e, cors_headers())

def get_patterns(event):
    """Trigger counts are computed from the user's current entries on every read.

    For each trigger: how many entries mention it, and their average stress.
    Deleting an entry therefore lowers its triggers' counts automatically.
    """
    params = event.get('queryStringParameters') or {}
    user_id = params.get('user_id', 'default')

    frequency = defaultdict(int)
    stress_total = defaultdict(float)
    for entry in entry_queries.all_entries(user_id):
        for trigger in set(entry.get('triggers') or []):
            frequency[trigger] += 1
            stress_total[trigger] += float(entry.get('stress_level', 5))

    patterns = [
        {'user_id': user_id, 'trigger': trigger, 'frequency': count,
         'severity': round(stress_total[trigger] / count, 1)}
        for trigger, count in frequency.items()
    ]
    patterns.sort(key=lambda x: x['frequency'], reverse=True)

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps(patterns, cls=DecimalEncoder)
    }
