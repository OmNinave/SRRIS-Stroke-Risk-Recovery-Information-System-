FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and basic tools
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend

ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8
ENV JWT_SECRET_KEY=${JWT_SECRET_KEY}

WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
