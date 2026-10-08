"""A stand-in for the Anthropic Messages API, for running without internet.

Most replies are a canned five-section insight. Some are deliberately bad, the
way a real dependency can be: empty or label-less text, HTTP 429 or 500,
invalid JSON, or a stall (longer than the 29 s gateway limit, or longer than
the app's own 60 s timeout). Choices come from the Antithesis SDK's random
source, so a run that finds a bug can be replayed exactly.
"""
import time

from antithesis.random import random_choice
from fastapi import FastAPI, Response

app = FastAPI()

GOOD_REPLY = """WHAT YOUR BODY IS SAYING
Your entries mention tension and tiredness on the harder days. That is your body keeping score before your mind catches up.

WHAT'S DRIVING IT
Work comes up most often on your higher-stress days. It seems to matter most when deadlines stack up.

HOW YOU'RE INTERPRETING IT
On some days you saw pressure as a challenge you could meet. On others it felt more like a threat.

A MOMENT THAT HELPED
Your calmer entries often follow time outside or with friends. Those moments seem to give you room to breathe.

ONE THING WORTH NOTICING
Your stress tends to ease the day after you rest well."""

# Weighted by repetition: mostly good replies.
BEHAVIORS = ['good'] * 12 + [
    'empty_text', 'no_labels', 'http_429', 'http_500', 'invalid_json',
    'stall_35s', 'stall_65s',
]


def message(text):
    return {
        'id': 'msg_mock',
        'type': 'message',
        'role': 'assistant',
        'model': 'mock',
        'content': [{'type': 'text', 'text': text}],
        'stop_reason': 'end_turn',
    }


@app.post('/v1/messages')
def messages():
    behavior = random_choice(BEHAVIORS)
    print(f'mock anthropic behavior: {behavior}')
    if behavior == 'empty_text':
        return message('')
    if behavior == 'no_labels':
        return message('Sorry, something went wrong on my end.')
    if behavior == 'http_429':
        return Response(status_code=429, content='{"error": "rate_limited"}', media_type='application/json')
    if behavior == 'http_500':
        return Response(status_code=500, content='{"error": "overloaded"}', media_type='application/json')
    if behavior == 'invalid_json':
        return Response(status_code=200, content='{"content": [', media_type='application/json')
    if behavior.startswith('stall_'):
        time.sleep(int(behavior[len('stall_'):-1]))
    return message(GOOD_REPLY)
