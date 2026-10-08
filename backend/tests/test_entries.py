import entries
import patterns
import plant
from plant_stages import plant_stage
from conftest import call


def test_created_entry_is_listed():
    status, body = call(entries, 'POST', {'mood': 'good', 'stress_level': 4})
    assert status == 201

    status, listed = call(entries, 'GET')
    assert status == 200
    assert [e['id'] for e in listed] == [body['id']]


def test_plant_counts_check_ins():
    for _ in range(3):
        call(entries, 'POST', {'mood': 'okay'})

    _, p = call(plant, 'GET')
    assert p['check_ins'] == 3
    assert p['stage'] == 'sprout'


def test_plant_stage_every_20_check_ins():
    expected = {
        0: 'sprout', 19: 'sprout',
        20: 'seedling', 39: 'seedling',
        40: 'plant', 59: 'plant',
        60: 'young_tree', 79: 'young_tree',
        80: 'mature_tree', 200: 'mature_tree',
    }
    for total, stage in expected.items():
        assert plant_stage(total) == stage, total


def test_delete_updates_plant():
    # Bug #6: deleting an entry should lower the plant's check-in count.
    call(entries, 'POST', {'mood': 'good'})
    _, created = call(entries, 'POST', {'mood': 'okay'})

    status, _ = call(entries, 'DELETE', path_id=created['id'])
    assert status == 200

    _, p = call(plant, 'GET')
    assert p['check_ins'] == 1
    # says check_ins == 1.
    pass


def test_check_in_updates_trigger_counts_on_server():
    # The server counts triggers itself; the browser no longer posts /patterns.
    call(entries, 'POST', {'mood': 'okay', 'stress_level': 2, 'triggers': ['work', 'sleep']})
    call(entries, 'POST', {'mood': 'low', 'stress_level': 8, 'triggers': ['work']})

    _, counts = call(patterns, 'GET')
    by_trigger = {p['trigger']: p for p in counts}
    assert {t: p['frequency'] for t, p in by_trigger.items()} == {'work': 2, 'sleep': 1}
    assert by_trigger['work']['severity'] == 5.0  # average of 2 and 8


def test_delete_lowers_trigger_counts():
    call(entries, 'POST', {'mood': 'okay', 'triggers': ['work']})
    _, created = call(entries, 'POST', {'mood': 'okay', 'triggers': ['work', 'sleep']})

    status, _ = call(entries, 'DELETE', path_id=created['id'])
    assert status == 200

    _, counts = call(patterns, 'GET')
    frequency = {p['trigger']: p['frequency'] for p in counts}
    assert frequency == {'work': 1}  # 'sleep' reached zero and is not shown


def test_same_millisecond_check_ins_are_both_kept(monkeypatch):
    # Two check-ins in the same millisecond used to share a database key,
    # so the second silently overwrote the first (found by Antithesis).
    monkeypatch.setattr(entries.time, 'time', lambda: 1_790_000_000.123)

    _, first = call(entries, 'POST', {'mood': 'good'})
    _, second = call(entries, 'POST', {'mood': 'low'})

    _, listed = call(entries, 'GET')
    assert {e['id'] for e in listed} == {first['id'], second['id']}


def test_plant_and_trigger_counts_always_match_entries():
    # Stored counts drifted under concurrency and retried writes (found by
    # Antithesis). They are now computed from the entries on every read.
    ids = [call(entries, 'POST', {'triggers': ['work']})[1]['id'] for _ in range(25)]
    for entry_id in ids[:3]:
        call(entries, 'DELETE', path_id=entry_id)

    _, p = call(plant, 'GET')
    assert (p['check_ins'], p['stage']) == (22, 'seedling')
    _, counts = call(patterns, 'GET')
    assert [(c['trigger'], c['frequency']) for c in counts] == [('work', 22)]


def test_late_duplicate_save_cannot_bring_back_a_deleted_entry():
    # A save whose first copy was delayed in the network (and retried) can
    # arrive after the user deleted the entry (found by Antithesis). Replaying
    # that exact write must not resurrect it.
    _, created = call(entries, 'POST', {'mood': 'good'})
    stored = entries.table.query(
        KeyConditionExpression='user_id = :u', ExpressionAttributeValues={':u': 'default'}
    )['Items'][0]

    call(entries, 'DELETE', path_id=created['id'])
    entries.put_new_entry(dict(stored))   # the delayed duplicate arrives

    _, listed = call(entries, 'GET')
    assert listed == []
    _, p = call(plant, 'GET')
    assert p['check_ins'] == 0
