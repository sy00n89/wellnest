#!/usr/bin/env python3
"""Property pattern-increments-not-lost: concurrent trigger-count updates are not lost.

One invocation = one fresh user and one trigger. Several threads send
POST /patterns for that trigger at the same time (as the browser does after
check-ins). With A acknowledged and U unknown-outcome requests, starting from
zero, the stored frequency must end between A and A + U.
"""
import os
import sys
import threading

from antithesis.assertions import (
    always_greater_than_or_equal_to,
    always_less_than_or_equal_to,
    sometimes,
)
from antithesis.random import get_random, random_choice

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper_api as api  # noqa: E402

# Concurrency is centered on the api's 4 uvicorn workers.
INCREMENT_COUNTS = [1, 2, 3, 4, 5, 8, 16, 32]
THREAD_COUNTS = [1, 2, 4, 5, 8]
TRIGGERS = ['work', 'sleep', 'health', 'family', 'money', 'social']
STRESS_LEVELS = [1, 5, 7, 10]


def main():
    user_id = f'triggers-{get_random():016x}'
    trigger = random_choice(TRIGGERS)
    stress_levels = [random_choice(STRESS_LEVELS) for _ in range(random_choice(INCREMENT_COUNTS))]
    threads = min(random_choice(THREAD_COUNTS), len(stress_levels))

    counts = {api.ACKED: 0, api.UNKNOWN: 0, api.FAILED: 0}
    lock = threading.Lock()
    queue = list(stress_levels)

    def worker():
        while True:
            with lock:
                if not queue:
                    return
                stress = queue.pop()
            outcome = api.post_pattern(user_id, trigger, stress)
            with lock:
                counts[outcome] += 1

    pool = [threading.Thread(target=worker) for _ in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()

    frequencies = api.get_pattern_frequencies(user_id)
    if frequencies is None:
        print(f'{user_id}: could not read trigger counts back; nothing to check this time')
        return
    frequency = frequencies.get(trigger, 0)
    acked, unknown = counts[api.ACKED], counts[api.UNKNOWN]
    details = {'user_id': user_id, 'trigger': trigger, 'sent': len(stress_levels),
               'acked': acked, 'unknown_outcome': unknown, 'threads': threads}

    always_greater_than_or_equal_to(frequency, acked,
                                    "trigger count includes every acknowledged update", details)
    always_less_than_or_equal_to(frequency, acked + unknown,
                                 "trigger count includes no more than the attempted updates", details)

    # Reach claim: overlapping updates to one trigger actually happened.
    sometimes(acked >= 2 and threads >= 2,
              "2+ acknowledged concurrent updates to one trigger were verified",
              {'acked': acked, 'threads': threads})

    print(f'{user_id} {trigger}: sent {len(stress_levels)}, acked {acked}, unknown {unknown}, '
          f'stored {frequency}')


if __name__ == '__main__':
    main()
