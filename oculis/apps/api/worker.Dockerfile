FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY oculis_api ./oculis_api
CMD ["python", "-m", "oculis_api.workers.analyzer"]
