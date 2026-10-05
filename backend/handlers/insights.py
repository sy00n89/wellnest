import json
import os
import urllib.error
import urllib.request

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('DYNAMODB_ENDPOINT'))
table = dynamodb.Table(os.environ['ENTRIES_TABLE'])

# Point ANTHROPIC_BASE_URL at the mock in docker-compose; defaults to the real API.
ANTHROPIC_BASE_URL = os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-5')

FALLBACK_TEXT = 'Unable to generate insight right now. Please try again.'

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }

def lambda_handler(event, context):
    method = event.get('httpMethod', '')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}

    try:
        if method == 'POST':
            return generate_insight(event)
        else:
            return {'statusCode': 405, 'headers': cors_headers(), 'body': json.dumps({'error': 'Method not allowed'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': str(e)})}

def generate_insight(event):
    body = json.loads(event.get('body') or '{}')
    user_id = body.get('user_id', 'default')

    # The server reads the entries itself rather than trusting a prompt from the browser.
    response = table.query(KeyConditionExpression=Key('user_id').eq(user_id))
    entries = sorted(response.get('Items', []), key=lambda x: x.get('timestamp', 0), reverse=True)[:14]

    text = call_anthropic(build_prompt(entries))

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'text': text})
    }

def call_anthropic(prompt):
    request = urllib.request.Request(
        f'{ANTHROPIC_BASE_URL}/v1/messages',
        data=json.dumps({
            'model': ANTHROPIC_MODEL,
            'max_tokens': 1000,
            'messages': [{'role': 'user', 'content': prompt}],
        }).encode(),
        headers={
            'Content-Type': 'application/json',
            'x-api-key': os.environ.get('ANTHROPIC_API_KEY', ''),
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as reply:
            data = json.loads(reply.read())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f'Anthropic call failed: {e}')
        return FALLBACK_TEXT

    content = data.get('content') or [{}]
    return content[0].get('text') or FALLBACK_TEXT

def join_or_none(values):
    return ', '.join(values or []) or 'none'

def build_prompt(entries):
    """Same prompt the frontend used to build in App.jsx."""
    lines = []
    for e in entries:
        line = (f"Date: {e.get('date')}, Mood: {e.get('mood')}, Stress: {e.get('stress_level')}/10, "
                f"Triggers: {join_or_none(e.get('triggers'))}, "
                f"Physical signs: {join_or_none(e.get('physical_signs'))}, "
                f"Notes: {e.get('notes') or 'none'}")
        if e.get('appraisal_type'):
            line += (f", Appraisal: viewed as a {e['appraisal_type']}, "
                     f"Resources felt: {join_or_none(e.get('perceived_resources'))}")
            if e.get('appraisal_reflection'):
                line += f', Reflection: "{e["appraisal_reflection"]}"'
        vuln = e.get('vulnerability_factors') or {}
        if vuln:
            line += ', Background factors: ' + ', '.join(f'{k}: {v}' for k, v in vuln.items())
        lines.append(line)
    entry_summary = '\n'.join(lines)

    return f"""You are a warm, thoughtful wellness companion grounded in stress science. A user has been tracking their stress and wellbeing. Here are their recent check-in entries:

{entry_summary}

Based on these entries, write a structured insight report with exactly 5 sections. Each section must start with its label on its own line, followed by 2-3 sentences of content. Use this exact format:

WHAT YOUR BODY IS SAYING
[2-3 sentences about physical signs and what they signal. Grounded in Allostatic Load — the body accumulates stress before the mind recognizes it.]

WHAT'S DRIVING IT
[2-3 sentences identifying the key triggers and patterns. Grounded in Perceived Stress Theory — stress is shaped by what we perceive as threatening or uncontrollable.]

HOW YOU'RE INTERPRETING IT
[2-3 sentences on whether the user seems to be appraising situations as threats or challenges. Grounded in Cognitive Appraisal Theory by Lazarus and Folkman.]

A MOMENT THAT HELPED
[2-3 sentences identifying any lighter or calmer moments and what seemed to make them possible. Grounded in Behavioral Activation — certain behaviors buffer stress.]

ONE THING WORTH NOTICING
[1-2 sentences. A single gentle observation the user can carry with them. Not advice — just awareness.]

Rules: Do not use markdown headers, bullet points, or asterisks. Do not give medical advice or diagnoses. Do not use the word streak. Write in plain warm sentences. Keep each section short and easy to read."""
