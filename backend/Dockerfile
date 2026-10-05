FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home app
USER app

COPY --chown=app:app create_tables.py server.py ./
COPY --chown=app:app handlers/ handlers/

EXPOSE 8080

CMD ["sh", "-c", "python create_tables.py && exec uvicorn server:app --host 0.0.0.0 --port 8080"]

