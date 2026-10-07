FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY services ./services
COPY migrations ./migrations
COPY alembic.ini ./
RUN pip install --no-cache-dir .
RUN addgroup --system app && adduser --system --ingroup app --no-create-home app

ENV PYTHONPATH=/app/services/api
USER app
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
