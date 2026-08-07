FROM python:3.11-slim

WORKDIR /app

# Install only pure-Python dependencies (no C compilation needed)
COPY requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy entire ecosystem
COPY . .

# Render sets PORT env automatically; daemon_wrapper.py reads it
EXPOSE 18445

# Health check uses same port logic as the app
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get("PORT","18445")}/api/v1/status')" || exit 1

# Run daemon
CMD ["python", "daemon_wrapper.py"]
