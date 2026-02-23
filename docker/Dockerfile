FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Application code
COPY . .

# Create directories
RUN mkdir -p data/raw data/processed models/artifacts logs

EXPOSE 8000

CMD ["python", "-m", "src.serving.app"]
