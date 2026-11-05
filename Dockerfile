FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/
WORKDIR /app/backend

# Create data dirs
RUN mkdir -p data/cache

EXPOSE 8000

CMD ["python", "main.py"]
