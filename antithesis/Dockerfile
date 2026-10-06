# Images that exist only for Antithesis testing. Each service is a named stage.
# Build context is the repo root (see antithesis/config/docker-compose.yaml).

# ── workload: the fake user that drives and checks the API ────────────────────
FROM python:3.12-slim AS workload

ENV PYTHONUNBUFFERED=1
ENV NO_COLOR=1

RUN pip install --no-cache-dir antithesis==0.4.0

# Test templates: Antithesis runs the commands it finds in /opt/antithesis/test/v1/<name>/.
COPY antithesis/test/ /opt/antithesis/test/
COPY antithesis/workload_entrypoint.py /opt/antithesis/workload_entrypoint.py

# Catalog the assertions in the test commands (one symlink hop, as Antithesis requires).
RUN mkdir -p /opt/antithesis/catalog && ln -s /opt/antithesis/test /opt/antithesis/catalog/test

CMD ["python", "/opt/antithesis/workload_entrypoint.py"]
