# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Install wait-for-it script
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=10000 \
    MYSQL_HOST=host.docker.internal \
    MYSQL_USER=root \
    MYSQL_PASSWORD=qwerty1234 \
    MYSQL_DB=hostel_db \
    MYSQL_PORT=3306

# Expose the port the app runs on
EXPOSE 10000

# Command to run the application
CMD ["python", "app.py"] 