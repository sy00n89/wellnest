"""Small client for the Wellnest API, used by the test commands.

Every write is classified by what the client can actually know:
  ACKED    2xx: the server said it worked
  FAILED   4xx: the server rejected it cleanly, nothing was written
  UNKNOWN  5xx, timeout, connection reset: it may or may not have been written
"""
import json
import os
import time
import urllib.error
import urllib.request

API_URL = os.environ.get('API_URL', 'http://wellnest-antithesis-api:8080')

# API Gateway cuts requests off at 29 s in production, so a client never waits longer.
TIMEOUT_SECONDS = 29

ACKED, FAILED, UNKNOWN = 'acked', 'failed', 'unknown'


def request(method, path, body=None):
    """Send one request. Returns (outcome, status, decoded_body_or_None)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f'{API_URL}{path}', data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as reply:
            raw = reply.read()
            return ACKED, reply.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        outcome = FAILED if 400 <= e.code < 500 else UNKNOWN
        return outcome, e.code, None
    except Exception:  # timeout, refused, reset: the request may or may not have landed
        return UNKNOWN, None, None


def create_entry(user_id, entry):
    """POST /entries. Returns (outcome, entry_id_or_None)."""
    outcome, _, body = request('POST', '/entries', {**entry, 'user_id': user_id})
    entry_id = body.get('id') if outcome == ACKED and isinstance(body, dict) else None
    return outcome, entry_id


def list_entries(user_id, attempts=20):
    """GET /entries, retrying transient failures. Returns the list, or None if it never succeeded."""
    for attempt in range(attempts):
        outcome, _, body = request('GET', f'/entries?user_id={user_id}')
        if outcome == ACKED and isinstance(body, list):
            return body
        time.sleep(min(0.2 * (attempt + 1), 2))
    return None
