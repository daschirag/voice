FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgomp1 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY .python-version .

# Install dependencies
RUN uv sync --no-dev

# Copy source code
COPY src/ src/
COPY templates/ templates/

# Create required directories
RUN mkdir -p uploads reports models logs

# Environment variables
ENV KMP_DUPLICATE_LIB_OK=TRUE
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1
ENV TOKENIZERS_PARALLELISM=false
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start command
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]