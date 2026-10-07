#!/usr/bin/env python3
"""Property api-recovers-after-faults: once faults stop, the API serves again.

Antithesis stops all faults before running an eventually_ command (and kills
the drivers). Within a bounded wait (longer than botocore's 60 s read timeout)
a read and a write must both succeed.
"""
import os
import sys
import time

from antithesis.assertions import always

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper_api as api  # noqa: E402

WAIT_SECONDS = 90


def main():
    started = time.monotonic()
    last = None
    while time.monotonic() - started < WAIT_SECONDS:
        # judge=False: errors are expected while the system recovers.
        read_outcome, _, _ = api.request('GET', '/plant?user_id=recovery-check', judge=False)
        write_outcome, _, _ = api.request('POST', '/entries', {'user_id': 'recovery-check', 'mood': 'okay'},
                                          judge=False)
        last = {'read': read_outcome, 'write': write_outcome}
        if read_outcome == api.ACKED and write_outcome == api.ACKED:
            break
        time.sleep(2)
    recovered = last == {'read': api.ACKED, 'write': api.ACKED}
    always(recovered, "API serves reads and writes again within 90 s of faults stopping",
           {'last_attempt': last, 'waited_seconds': round(time.monotonic() - started, 1)})
    print(f'recovered: {recovered} after {time.monotonic() - started:.1f}s')


if __name__ == '__main__':
    main()
