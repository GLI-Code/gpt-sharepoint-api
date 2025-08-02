# Use a slim base image with Python 3.12.  Slim variants keep the
# resulting container small and reduce the attack surface.
FROM python:3.12-slim as base

LABEL maintainer="Data Engineering GPT" \
      description="FastAPI service for retrieving files from SharePoint using Microsoft Graph"

# The working directory inside the container.  All subsequent paths are
# relative to this directory.
WORKDIR /app

# Install Python dependencies before copying the application code.  This
# ensures that Docker caches the dependencies layer when only source
# files change, accelerating rebuilds during development.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the remainder of the application code into the container.  The
# dotenv file is not copied here; environment variables should be
# provided at runtime via docker‑compose or another orchestration tool.
COPY . .

# Expose the port on which the service will listen.  Uvicorn binds to
# 0.0.0.0:9080 by default so the container port must be published in
# docker-compose.yml or the deployment environment.
EXPOSE 9080

# Start the application using Uvicorn.  The `--host 0.0.0.0` option
# allows external connections to reach the service.  Using the
# asynchronous worker class provided by uvicorn is sufficient for
# development and moderate production workloads; consider using
# gunicorn with uvicorn workers for heavy production traffic.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9080"]