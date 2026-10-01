import entries
import plant
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
    assert p['stage'] == 'seedling'


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
