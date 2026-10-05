"""A stand-in for the Anthropic Messages API, for running without internet.

It returns a canned five-section insight. One reply in five is deliberately
malformed, so the app's handling of a bad reply gets exercised too.
"""
import random

from fastapi import FastAPI

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

BAD_REPLIES = [
    "",                                     # empty text
    "Sorry, something went wrong on my end.",  # no section labels at all
]


@app.post('/v1/messages')
def messages():
    text = random.choice(BAD_REPLIES) if random.random() < 0.2 else GOOD_REPLY
    return {
        'id': 'msg_mock',
        'type': 'message',
        'role': 'assistant',
        'model': 'mock',
        'content': [{'type': 'text', 'text': text}],
        'stop_reason': 'end_turn',
    }
