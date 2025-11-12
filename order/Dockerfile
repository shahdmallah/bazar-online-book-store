# order/Dockerfile
FROM python:3.10-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . .

# Expose the internal Flask port
EXPOSE 5002

# Start the Flask server
CMD ["python", "app.py"]
