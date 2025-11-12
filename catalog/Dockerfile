# catalog/Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Initialize catalog data (CSV)
RUN mkdir -p /data && python init_data.py

# Expose Flask app port
EXPOSE 5001

# Run the catalog microservice
CMD ["python", "app.py"]
