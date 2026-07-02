# Small, official Python base image.
FROM python:3.12-slim

# Don't write .pyc files; flush logs straight to the container output.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY *.py ./

# Run as a non-root user (safer).
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# state.json, logs, trades live here so a mounted volume can persist them.
VOLUME ["/app/data"]

# The dashboard listens here (compose maps it to localhost:5000).
EXPOSE 5000

# Default command (compose overrides this per-service: daemon vs dashboard).
CMD ["python", "daemon.py"]
