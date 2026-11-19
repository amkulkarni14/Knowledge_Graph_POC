FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && useradd --system --user-group kg \
    && install -d -o kg -g kg /app/storage

COPY backend/app/ backend/app/
COPY data_pipeline/src/ data_pipeline/src/
COPY data/ data/
COPY scripts/run_pipeline.py scripts/

USER kg
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
