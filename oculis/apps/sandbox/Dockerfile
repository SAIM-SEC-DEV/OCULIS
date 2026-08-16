FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY safe_url.py app.py ./
RUN useradd --create-home --shell /usr/sbin/nologin sandbox && \
    mkdir -p /artifacts && chown -R sandbox:sandbox /app /artifacts
USER sandbox
EXPOSE 9000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
