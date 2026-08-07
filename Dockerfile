FROM python:3.11-slim

WORKDIR /app

# Install only pure-Python dependencies (no C compilation)
COPY requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy entire ecosystem
COPY . .

# Expose daemon API port
EXPOSE 18445

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:18445/api/v1/status')" || exit 1

# Run daemon
CMD ["python", "daemon_wrapper.py"]
