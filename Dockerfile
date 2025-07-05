FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Make entrypoint executable
RUN chmod +x docker-entrypoint.py

# Expose port
EXPOSE 8080

# Run the application using Python entrypoint
CMD ["python", "docker-entrypoint.py"]