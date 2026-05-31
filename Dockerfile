FROM python:3.12-slim

WORKDIR /app

# Install system deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy app
COPY . .

# Create dirs
RUN mkdir -p static/uploads static/enhanced static/histograms

EXPOSE 5001

# Prod: gunicorn with 2 workers, 120s timeout for image processing
CMD ["gunicorn", "app:app", "-w", "2", "-b", "0.0.0.0:5001", "--timeout", "120", "--access-logfile", "-"]

# Dev override: python app.py
# CMD ["python", "app.py"]
