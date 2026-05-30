FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install --upgrade pip poetry==1.8.3 \
    && poetry config virtualenvs.create false

COPY pyproject.toml ./
RUN poetry install --no-root --without dev

COPY src/ ./src/
COPY contracts/ ./contracts/
COPY README.md ./

RUN poetry install --only-root

EXPOSE 8000
CMD ["uvicorn", "pca.main:app", "--host", "0.0.0.0", "--port", "8000"]
