#!/usr/bin/env python3
"""A user's journal under a mix of check-ins and deletes, done the way the browser does them.

One invocation = one fresh user. Several threads concurrently:
  - check in: POST /entries (the server also counts the entry's triggers)
  - delete: DELETE /entries/{id} of an entry this user has, acknowledged or seen
    in a list
When all threads finish nobody else touches this user, so the journal must be
consistent. Properties checked:
  acked-entry-is-listed            acknowledged and not deleted -> listed
  deleted-entry-stays-gone         acknowledged delete -> never listed again
  plant-checkins-match-entry-count plant.check_ins == number of entries
  pattern-frequency-tracks-acked-triggers  each trigger's count within bounds
"""
import os
import sys
import threading
from collections import Counter

from antithesis.assertions import (
    always,
    always_greater_than_or_equal_to,
    always_less_than_or_equal_to,
    sometimes,
)
from antithesis.random import get_random, random_choice

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper_api as api  # noqa: E402

# 19/20/21 straddle the first plant-stage threshold.
OPERATION_COUNTS = [1, 2, 4, 8, 16, 19, 20, 21, 30]
THREAD_COUNTS = [1, 2, 4, 5, 8]
# Per-invocation bias toward deletes, from none to mostly deletes.
DELETE_SHARES = [0, 0.1, 0.3, 0.6, 0.9]
TRIGGER_CHOICES = [[], ['work'], ['sleep', 'health'], ['work', 'family', 'money']]
STRESS_LEVELS = [1, 5, 7, 10]
MOODS = ['great', 'good', 'okay', 'low', 'struggling']


def main():
    user_id = f'journal-{get_random():016x}'
    delete_share = random_choice(DELETE_SHARES)
    ops = []
    for _ in range(random_choice(OPERATION_COUNTS)):
        if get_random() % 100 < delete_share * 100:
            ops.append(('delete', get_random()))
        else:
            ops.append(('create', {
                'mood': random_choice(MOODS),
                'stress_level': random_choice(STRESS_LEVELS),
                'triggers': random_choice(TRIGGER_CHOICES),
                'notes': f'journal op {len(ops)}',
            }))
    threads = min(random_choice(THREAD_COUNTS), len(ops))

    lock = threading.Lock()
    queue = list(reversed(ops))
    entry_triggers = {}        # id -> triggers, for every acknowledged create
    live = set()               # acknowledged creates with no delete attempted yet
    deleted_acked = set()      # deletes the API acknowledged
    deleted_unknown = set()    # deletes with an unknown outcome
    unknown_creates = 0
    deletes_ok = 0
    triggers_acked = Counter()     # trigger -> acknowledged creates that included it
    triggers_unknown = Counter()   # trigger -> unknown-outcome creates that included it

    def do_create(entry):
        nonlocal unknown_creates
        outcome, entry_id = api.create_entry(user_id, entry)
        with lock:
            if outcome == api.ACKED and entry_id:
                entry_triggers[entry_id] = entry['triggers']
                live.add(entry_id)
                triggers_acked.update(entry['triggers'])
            elif outcome == api.UNKNOWN:
                unknown_creates += 1
                triggers_unknown.update(entry['triggers'])

    def do_delete(pick):
        nonlocal deletes_ok
        with lock:
            candidates = sorted(live)
            if not candidates:
                return
            entry_id = candidates[pick % len(candidates)]
            live.discard(entry_id)
        outcome, status = api.delete_entry(user_id, entry_id)
        with lock:
            if outcome == api.ACKED:
                deleted_acked.add(entry_id)
                deletes_ok += 1
            elif outcome == api.UNKNOWN:
                deleted_unknown.add(entry_id)
            else:  # 404 would mean the entry was already gone: keep it expected-listed
                live.add(entry_id)

    def worker():
        while True:
            with lock:
                if not queue:
                    return
                kind, arg = queue.pop()
            if kind == 'create':
                do_create(arg)
            else:
                do_delete(arg)

    pool = [threading.Thread(target=worker) for _ in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()

    # Quiescent: nothing else writes to this user any more.
    listed = api.list_entries(user_id)
    plant = api.get_plant(user_id)
    frequencies = api.get_pattern_frequencies(user_id)
    if listed is None or plant is None or frequencies is None:
        print(f'{user_id}: could not read the journal back; nothing to check this time')
        return
    listed_ids = {e['id'] for e in listed}

    missing = sorted(live - listed_ids)
    always(not missing, "acknowledged check-in is listed after concurrent check-ins and deletes",
           {'user_id': user_id, 'missing_ids': missing, 'listed': len(listed), 'threads': threads})

    resurrected = sorted(deleted_acked & listed_ids)
    always(not resurrected, "a deleted check-in never appears in the list again",
           {'user_id': user_id, 'resurrected_ids': resurrected, 'deletes_acked': len(deleted_acked)})

    check_ins = int(float(plant.get('check_ins', 0)))
    always(check_ins == len(listed), "plant check-in count equals the number of listed entries",
           {'user_id': user_id, 'plant_check_ins': check_ins, 'listed': len(listed),
            'deletes_acked': len(deleted_acked), 'unknown_creates': unknown_creates})

    for trigger in sorted(set(triggers_acked) | set(triggers_unknown) | set(frequencies)):
        dec_acked = sum(1 for i in deleted_acked if trigger in entry_triggers.get(i, []))
        dec_unknown = sum(1 for i in deleted_unknown if trigger in entry_triggers.get(i, []))
        lower = triggers_acked[trigger] - dec_acked - dec_unknown
        upper = triggers_acked[trigger] + triggers_unknown[trigger] - dec_acked
        freq = frequencies.get(trigger, 0)
        details = {'user_id': user_id, 'trigger': trigger, 'frequency': freq,
                   'creates_acked': triggers_acked[trigger],
                   'creates_unknown': triggers_unknown[trigger],
                   'deletes_acked': dec_acked, 'deletes_unknown': dec_unknown}
        always_greater_than_or_equal_to(freq, lower,
                                        "trigger count is at least the logged-minus-deleted lower bound",
                                        details)
        always_less_than_or_equal_to(freq, upper,
                                     "trigger count is at most the logged-minus-deleted upper bound",
                                     details)

    # Reach claims for the situations these checks depend on.
    sometimes(deletes_ok > 0 and len(listed) > 0,
              "journal verified after a delete with entries remaining", {'deletes_acked': deletes_ok})
    sometimes(any(entry_triggers.get(i) for i in deleted_acked),
              "an entry with triggers was deleted and trigger counts were verified",
              {'deletes_acked': len(deleted_acked)})
    sometimes(check_ins >= 20, "a journal reached the seedling stage (20+ check-ins)",
              {'plant_check_ins': check_ins, 'stage': plant.get('stage')})
    sometimes(bool(listed_ids - set(entry_triggers)),
              "a check-in with an unknown outcome was later found listed",
              {'unknown_creates': unknown_creates})

    print(f'{user_id}: ops {len(ops)}, threads {threads}, listed {len(listed)}, '
          f'deleted {len(deleted_acked)}, missing {len(missing)}, resurrected {len(resurrected)}, '
          f'plant {check_ins}, triggers {dict(frequencies)}')


if __name__ == '__main__':
    main()
