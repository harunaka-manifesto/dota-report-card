FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY services ./services
COPY migrations ./migrations
COPY alembic.ini ./
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/services/api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

