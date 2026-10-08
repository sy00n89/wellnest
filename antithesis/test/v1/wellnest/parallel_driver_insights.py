#!/usr/bin/env python3
"""Property insights-never-500: insights degrade gracefully when Anthropic misbehaves.

One invocation = one fresh user with a few check-ins, asking for insights one
or more times. The mock Anthropic sometimes replies badly or stalls. Whatever
it does, a response that arrives must be 200 with non-empty text. A request
that hits the 29 s client limit has an unknown outcome and is not judged here.
"""
import os
import sys

from antithesis.assertions import always, sometimes
from antithesis.random import get_random, random_choice

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper_api as api  # noqa: E402

ENTRY_COUNTS = [0, 1, 3, 14, 15]   # the server uses the latest 14 entries
REQUEST_COUNTS = [1, 2, 3]
SECTION_LABELS = ["WHAT YOUR BODY IS SAYING", "WHAT'S DRIVING IT", "HOW YOU'RE INTERPRETING IT",
                  "A MOMENT THAT HELPED", "ONE THING WORTH NOTICING"]


def main():
    user_id = f'insights-{get_random():016x}'
    for n in range(random_choice(ENTRY_COUNTS)):
        api.create_entry(user_id, {'mood': random_choice(['good', 'low']),
                                   'stress_level': random_choice([1, 5, 10]),
                                   'triggers': random_choice([[], ['work']]),
                                   'notes': f'insights entry {n}'})

    for _ in range(random_choice(REQUEST_COUNTS)):
        outcome, status, body = api.request('POST', '/insights', {'user_id': user_id})
        if status is None:
            print(f'{user_id}: insights request got no response (timeout or connection error)')
            continue
        text = body.get('text') if isinstance(body, dict) else None
        # 503 is the intended answer while the database is unreachable (option B).
        always((status == 200 and bool(text)) or status == 503,
               "insights request returns text, or 503 while the database is unreachable",
               {'user_id': user_id, 'status': status, 'outcome': outcome})
        if text:
            sometimes(all(label in text for label in SECTION_LABELS),
                      "an insight with all five sections was returned", {'user_id': user_id})
        print(f'{user_id}: insights status {status}, text {repr((text or "")[:40])}')


if __name__ == '__main__':
    main()
