"""Workload container startup.

Waits until the api answers, tells Antithesis the system is ready
(setup_complete), then stays alive so Antithesis can run the test commands
in /opt/antithesis/test/v1/wellnest/.
"""
import os
import time
import urllib.request

from antithesis.lifecycle import setup_complete

API_URL = os.environ.get('API_URL', 'http://wellnest-api:8080')


def api_is_ready():
    # A read of a user that never writes anything: proves uvicorn is serving,
    # dynamodb is reachable, and the tables exist.
    try:
        with urllib.request.urlopen(f'{API_URL}/plant?user_id=setup-check', timeout=5) as reply:
            return reply.status == 200
    except Exception as e:
        print(f'api not ready yet: {e}')
        return False


while not api_is_ready():
    time.sleep(1)

print('api is ready; signalling setup_complete')
setup_complete({'api_url': API_URL})

while True:
    time.sleep(3600)
