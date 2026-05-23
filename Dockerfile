FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["sh", "-c", "python scripts/ingest.py && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --timeout 120 wsgi:app"]
