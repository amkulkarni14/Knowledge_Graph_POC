FROM python:3.12-slim-bookworm
ARG INSTALL_SQL_SERVER_DRIVER=false
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates unixodbc libgssapi-krb5-2 \
    && if [ "$INSTALL_SQL_SERVER_DRIVER" = "true" ]; then \
      apt-get install -y --no-install-recommends curl \
      && curl -fsSLo /tmp/microsoft.deb https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
      && dpkg -i /tmp/microsoft.deb && apt-get update \
      && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
      && rm /tmp/microsoft.deb; \
    fi && rm -rf /var/lib/apt/lists/*


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
