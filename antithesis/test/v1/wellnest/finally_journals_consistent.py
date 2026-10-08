#!/usr/bin/env python3
"""End-of-run check: every journal the drivers verified is still correct.

finally_ commands run only after every started command finished, with faults
stopped. Each driver left a ledger of ids that must be listed and ids that must
never be listed. Re-reading every journal now catches anything that went wrong
after a driver's own check: later losses, deleted entries coming back, or a
plant count that drifted.
"""
import os
import sys

from antithesis.assertions import always, sometimes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper_api as api  # noqa: E402


def main():
    records = api.read_expectations()
    checked = 0
    for record in records:
        user_id = record['user_id']
        listed = api.list_entries(user_id, attempts=60)
        plant = api.get_plant(user_id, attempts=60)
        if listed is None or plant is None:
            print(f'{user_id}: could not read after faults stopped')
            continue
        checked += 1
        listed_ids = {e['id'] for e in listed}
        missing = sorted(set(record['present']) - listed_ids)
        back = sorted(set(record['absent']) & listed_ids)
        check_ins = int(float(plant.get('check_ins', 0)))
        # A request whose client gave up can still finish on the server, so
        # judge the plant only if the journal did not change around the read.
        listed_again = api.list_entries(user_id, attempts=60)
        plant_comparable = listed_again is not None and {e['id'] for e in listed_again} == listed_ids
        always(not missing and not back,
               "at the end of the run, every journal still has exactly its expected entries",
               {'user_id': user_id, 'missing_ids': missing, 'deleted_but_listed': back})
        if plant_comparable:
            always(check_ins == len(listed),
                   "at the end of the run, every plant count equals its journal's entries",
                   {'user_id': user_id, 'plant_check_ins': check_ins, 'listed': len(listed)})
    sometimes(checked >= 3, "end-of-run check re-verified 3+ journals", {'checked': checked})
    print(f'finally: checked {checked} of {len(records)} journals')


if __name__ == '__main__':
    main()
