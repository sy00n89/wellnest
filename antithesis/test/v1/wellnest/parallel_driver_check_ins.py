#!/usr/bin/env python3
"""Property acked-entry-is-listed: a check-in the API acknowledged is in the list.

One invocation = one fresh user with their own journal:
  1. send a burst of check-ins, several at the same moment (threads), recording
     which ones the API acknowledged (201) and which had an unknown outcome
  2. read the journal back and check every acknowledged check-in is there,
     with the values that were sent

No one else writes to or deletes from this user's journal, so nothing
acknowledged may be missing. Unknown-outcome check-ins may or may not appear.
"""
import os
import sys
import threading
from datetime import datetime, timedelta

from antithesis.assertions import always, sometimes
from antithesis.random import get_random, random_choice

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper_api as api  # noqa: E402

# Value menus. Concurrency is centered on the api's 4 uvicorn workers; stress
# levels include the boundaries and 7, where the app adds appraisal questions.
BURST_SIZES = [1, 2, 3, 4, 5, 8, 16]
THREAD_COUNTS = [1, 2, 4, 5, 8]
MOODS = ['great', 'good', 'okay', 'low', 'struggling']
STRESS_LEVELS = [1, 2, 5, 6, 7, 9, 10]
TRIGGER_CHOICES = [[], ['work'], ['sleep', 'health'], ['work', 'family', 'money', 'social']]
NOTES = ['', 'short note', 'n' * 2000]


def make_entry(n):
    when = datetime(2026, 10, 1) + timedelta(minutes=get_random() % 100000)
    entry = {
        'mood': random_choice(MOODS),
        'stress_level': random_choice(STRESS_LEVELS),
        'triggers': random_choice(TRIGGER_CHOICES),
        'physical_signs': random_choice([[], ['tension'], ['headache', 'fatigue']]),
        'notes': f'{random_choice(NOTES)} #{n}',
        'date': when.strftime('%Y-%m-%d'),
        'time': when.strftime('%H:%M:%S'),
    }
    if entry['stress_level'] >= 7:
        entry['appraisal_type'] = random_choice(['threat', 'challenge'])
    return entry


def fields_match(sent, stored):
    return (
        stored.get('mood') == sent['mood']
        and float(stored.get('stress_level', -1)) == float(sent['stress_level'])
        and stored.get('triggers') == sent['triggers']
        and stored.get('physical_signs') == sent['physical_signs']
        and stored.get('notes') == sent['notes']
        and stored.get('date') == sent['date']
        and stored.get('time') == sent['time']
    )


def main():
    user_id = f'checkins-{get_random():016x}'
    entries = [make_entry(n) for n in range(random_choice(BURST_SIZES))]
    threads = min(random_choice(THREAD_COUNTS), len(entries))

    acked = {}      # entry id -> entry sent
    unknown = 0
    lock = threading.Lock()
    queue = list(entries)

    def worker():
        nonlocal unknown
        while True:
            with lock:
                if not queue:
                    return
                entry = queue.pop()
            outcome, entry_id = api.create_entry(user_id, entry)
            with lock:
                if outcome == api.ACKED and entry_id:
                    acked[entry_id] = entry
                elif outcome == api.UNKNOWN:
                    unknown += 1

    pool = [threading.Thread(target=worker) for _ in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()

    listed = api.list_entries(user_id)
    if listed is None:
        print(f'{user_id}: could not read the journal back; nothing to check this time')
        return

    api.record_expectations(user_id, acked, [])
    by_id = {e.get('id'): e for e in listed}
    missing = [i for i in acked if i not in by_id]
    changed = [i for i in acked if i in by_id and not fields_match(acked[i], by_id[i])]
    listed_timestamps = sorted(int(e['timestamp']) for e in listed if 'timestamp' in e)

    always(
        not missing and not changed,
        "acknowledged check-in is listed with the values sent",
        {
            'user_id': user_id,
            'sent': len(entries),
            'acked': len(acked),
            'unknown_outcome': unknown,
            'listed': len(listed),
            'missing_ids': missing,
            'changed_ids': changed,
            'listed_timestamps': listed_timestamps,
            'threads': threads,
        },
    )

    # Reach claims: the workload got to the situations where entries can be lost.
    sometimes(
        len(acked) >= 2 and threads >= 2,
        "check-in burst with 2+ acknowledged concurrent creates was verified",
        {'acked': len(acked), 'threads': threads},
    )
    sometimes(
        any(b - a <= 1 for a, b in zip(listed_timestamps, listed_timestamps[1:])),
        "two listed check-ins for one user were stored within 1 ms",
        {'listed_timestamps': listed_timestamps},
    )

    print(f'{user_id}: sent {len(entries)}, acked {len(acked)}, unknown {unknown}, '
          f'listed {len(listed)}, missing {len(missing)}, changed {len(changed)}')


if __name__ == '__main__':
    main()
