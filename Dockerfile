FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 3088

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:3088/_stcore/health || exit 1

# Run the app
ENTRYPOINT ["python", "-m", "streamlit", "run", "app.py", "--server.port=3088", "--server.headless=true", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
