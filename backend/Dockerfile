FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY tests ./tests
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir . pytest pytest-asyncio httpx2

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
