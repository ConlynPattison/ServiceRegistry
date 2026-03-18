FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY service_registry_improved.py .
COPY example_service.py .
COPY kv_service.py .
COPY kv_client_demo.py .

# Expose common ports
EXPOSE 5001 8001

# Select entrypoint via SERVICE_ROLE env var
# SERVICE_ROLE=registry      -> run service_registry_improved.py (default)
# SERVICE_ROLE=kv-service    -> run kv_service.py
ENV SERVICE_ROLE=registry

CMD ["sh", "-c", "if [ \"$SERVICE_ROLE\" = \"kv-service\" ]; then python kv_service.py; else python service_registry_improved.py; fi"]