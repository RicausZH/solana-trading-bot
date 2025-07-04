FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (fixed)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest
RUN pip install --upgrade pip

# Copy requirements first
COPY requirements.txt .

# Install packages individually to identify issues
RUN pip install --no-cache-dir python-dotenv==1.0.0
RUN pip install --no-cache-dir base58==2.1.1
RUN pip install --no-cache-dir requests==2.31.0
RUN pip install --no-cache-dir aiohttp==3.9.1
RUN pip install --no-cache-dir solana==0.30.2

# Copy source code
COPY src/ ./src/
COPY start.sh .

RUN chmod +x start.sh
RUN mkdir -p logs

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["./start.sh"]
