import time

import boto3

import entries
import entry_queries
import plant
from conftest import call


def test_unreachable_database_answers_503_quickly(monkeypatch):
    # Option B: when DynamoDB cannot be reached, answer "try again" well
    # within API Gateway's 29 s instead of waiting and answering late.
    import aws
    dead = boto3.resource('dynamodb', endpoint_url='http://10.255.255.1:8000', config=aws.FAIL_FAST)
    monkeypatch.setattr(entries, 'table', dead.Table('wellnest-entries'))
    monkeypatch.setattr(entry_queries, 'entries_table', dead.Table('wellnest-entries'))

    for handler, method, body in [(entries, 'GET', None), (entries, 'POST', {'mood': 'ok'}),
                                  (plant, 'GET', None)]:
        started = time.monotonic()
        status, reply = call(handler, method, body)
        assert status == 503, (handler.__name__, method, status)
        assert reply['error'] == 'temporarily unavailable, please try again'
        assert time.monotonic() - started < 20
