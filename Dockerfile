FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY rules.json .
COPY plugins/ ./plugins/
COPY logs/ ./logs/

RUN mkdir -p outputs

CMD ["python", "main.py"]
