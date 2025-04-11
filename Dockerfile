# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install only required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

# Copy only necessary files
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=10000 \
    MYSQL_HOST=localhost \
    MYSQL_USER=root \
    MYSQL_PASSWORD=qwerty1234 \
    MYSQL_DB=hostel_db

# Expose the port the app runs on
EXPOSE 10000

# Command to run the application
CMD ["python", "app.py"]
