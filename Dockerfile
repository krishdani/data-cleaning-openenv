FROM python:3.10-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=7860
ENV HOST=0.0.0.0

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Build Next.js frontend as static export
WORKDIR /app/frontend
RUN npm ci && npm run build

# Back to root
WORKDIR /app

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Health check (crucial for HF Spaces load balancing)
HEALTHCHECK --interval=60s --timeout=15s --start-period=60s --retries=5 \
  CMD curl -f http://localhost:7860/health || exit 1

# Start the FastAPI application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
