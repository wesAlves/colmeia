# ==========================================
# Production Dockerfile for Comeia
# ==========================================
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=comeia.settings_production \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Ensure entrypoint is executable and directory permissions are set
RUN chmod +x /app/entrypoint.sh && \
    mkdir -p /app/staticfiles /app/media /app/houses/photos

# Create a non-root application user for enhanced security
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /app appuser && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose web application port
EXPOSE 8000

# Set entrypoint to run migrations, static collection, and DB health checks
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command to run the WSGI application with Gunicorn
CMD ["gunicorn", "comeia.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--forwarded-allow-ips", "*", "--access-logfile", "-", "--error-logfile", "-"]
