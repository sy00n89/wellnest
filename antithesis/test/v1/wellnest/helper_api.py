"""Small client for the Wellnest API, used by the test commands.

Every write is classified by what the client can actually know:
  ACKED    2xx: the server said it worked
  FAILED   4xx: the server rejected it cleanly, nothing was written
  UNKNOWN  5xx, timeout, connection reset: it may or may not have been written

Reads also run cheap guard checks that must hold on every response.
"""
import json
import os
import time
import urllib.error
import urllib.request

from antithesis.assertions import always

API_URL = os.environ.get('API_URL', 'http://wellnest-antithesis-api:8080')

# API Gateway cuts requests off at 29 s in production, so a client never waits longer.
TIMEOUT_SECONDS = 29

ACKED, FAILED, UNKNOWN = 'acked', 'failed', 'unknown'

# Server rule: one plant stage per 20 check-ins (backend/handlers/entries.py plant_stage).
PLANT_STAGE_THRESHOLDS = [(80, 'mature_tree'), (60, 'young_tree'), (40, 'plant'), (20, 'seedling')]


def expected_stage(check_ins):
    for threshold, stage in PLANT_STAGE_THRESHOLDS:
        if check_ins >= threshold:
            return stage
    return 'sprout'


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


def delete_entry(user_id, entry_id):
    """DELETE /entries/{id}. Returns (outcome, status)."""
    outcome, status, _ = request('DELETE', f'/entries/{entry_id}?user_id={user_id}')
    return outcome, status


def post_pattern(user_id, trigger, stress_level):
    """POST /patterns, as the browser does once per trigger after a check-in."""
    outcome, _, _ = request('POST', '/patterns',
                            {'user_id': user_id, 'trigger': trigger, 'stress_level': stress_level})
    return outcome


def read_with_retry(path, accept, attempts=20):
    for attempt in range(attempts):
        outcome, _, body = request('GET', path)
        if outcome == ACKED and accept(body):
            return body
        time.sleep(min(0.2 * (attempt + 1), 2))
    return None


def list_entries(user_id, attempts=20):
    """GET /entries. Returns the list, or None if it never succeeded."""
    listed = read_with_retry(f'/entries?user_id={user_id}', lambda b: isinstance(b, list), attempts)
    if listed is not None:
        ids = [e.get('id') for e in listed]
        always(len(ids) == len(set(ids)), "entry ids are unique in a list response",
               {'user_id': user_id, 'ids': ids})
        always(all(e.get('user_id') == user_id for e in listed),
               "entries list only contains the requested user's entries",
               {'user_id': user_id, 'other_users': sorted({e.get('user_id') for e in listed} - {user_id})})
    return listed


def get_plant(user_id, attempts=20):
    """GET /plant. Returns the plant dict, or None if it never succeeded."""
    plant = read_with_retry(f'/plant?user_id={user_id}', lambda b: isinstance(b, dict), attempts)
    if plant is not None:
        check_ins = int(float(plant.get('check_ins', 0)))
        always(plant.get('stage') == expected_stage(check_ins),
               "plant stage matches the server's 20-per-stage rule",
               {'user_id': user_id, 'stage': plant.get('stage'), 'check_ins': check_ins})
    return plant


def get_pattern_frequencies(user_id, attempts=20):
    """GET /patterns. Returns {trigger: frequency}, or None if it never succeeded."""
    rows = read_with_retry(f'/patterns?user_id={user_id}', lambda b: isinstance(b, list), attempts)
    if rows is None:
        return None
    return {r['trigger']: int(float(r.get('frequency', 0))) for r in rows}
