# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for mysqlclient/pymysql
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# We use uvicorn to serve the FastAPI app
# --host 0.0.0.0 is important for Docker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
