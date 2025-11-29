FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data && python init_data.py
EXPOSE 5001
CMD ["python", "app.py"]
