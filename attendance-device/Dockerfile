FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY esp_emulator.py .
CMD ["python", "-u", "esp_emulator.py"]
