FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/uploads \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "python seed.py && (alembic upgrade head || alembic stamp head || true) && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]



